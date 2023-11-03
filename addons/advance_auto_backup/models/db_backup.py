# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, _
from odoo.addons.google_drive.models.google_drive import GoogleDrive
from odoo.exceptions import Warning, ValidationError
import odoo
from odoo.http import content_disposition
import pytz
import requests
import logging
_logger = logging.getLogger(__name__)
from ftplib import FTP
import os
import datetime

try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib
import time
import base64
import socket
import json

import stat

try:
    import paramiko
except ImportError:
    raise ImportError(
        'This module needs paramiko to automatically write backups to the FTP through SFTP. Please install paramiko on your system. (sudo pip3 install paramiko)')


def execute(connector, method, *args):
    res = False
    try:
        res = getattr(connector, method)(*args)
    except socket.error as error:
        _logger.critical('Error while executing the method "execute". Error: ' + str(error))
        raise error
    return res


class db_backup(models.Model):
    _name = 'db.backup'
    _description = 'Backup configuration record'

    @api.multi
    def get_db_list(self, host, port, context={}):
        uri = 'http://' + host + ':' + port
        conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
        db_list = execute(conn, 'list')
        return db_list

    @api.multi
    def _get_db_name(self):
        dbName = self._cr.dbname
        return dbName

    # Columns for local server configuration
    host = fields.Char('Host', required=True, default='localhost')
    port = fields.Char('Port', required=True, default=8069)
    name = fields.Char('Database', required=True, help='Database you want to schedule backups for',
                       default=_get_db_name)
    folder = fields.Char('Backup Directory', help='Absolute path for storing the backups', required='True',
                         default='/odoo/backups')
    backup_type = fields.Selection([('zip', 'Zip'), ('dump', 'Dump')], 'Backup Type', required=True, default='zip')
    autoremove = fields.Boolean('Auto. Remove Backups',
                                help='If you check this option you can choose to automaticly remove the backup after xx days')
    days_to_keep = fields.Integer('Remove after x days',
                                  help="Choose after how many days the backup should be deleted. For example:\nIf you fill in 5 the backups will be removed after 5 days.",
                                  required=True)

    # Columns for external server (SFTP)
    sftp_write = fields.Boolean('Write to external server with sftp',
                                help="If you check this option you can specify the details needed to write to a remote server with SFTP.")
    sftp_path = fields.Char('Path external server',
                            help='The location to the folder where the dumps should be written to. For example /odoo/backups/.\nFiles will then be written to /odoo/backups/ on your remote server.')
    sftp_host = fields.Char('IP Address SFTP Server',
                            help='The IP address from your remote server. For example 192.168.0.1')
    sftp_port = fields.Integer('SFTP Port', help='The port on the FTP server that accepts SSH/SFTP calls.', default=22)
    sftp_user = fields.Char('Username SFTP Server',
                            help='The username where the SFTP connection should be made with. This is the user on the external server.')
    sftp_password = fields.Char('Password User SFTP Server',
                                help='The password from the user where the SFTP connection should be made with. This is the password from the user on the external server.')
    days_to_keep_sftp = fields.Integer('Remove SFTP after x days',
                                       help='Choose after how many days the backup should be deleted from the FTP server. For example:\nIf you fill in 5 the backups will be removed after 5 days from the FTP server.',
                                       default=30)
    send_mail_sftp_fail = fields.Boolean('Auto. E-mail on backup fail',
                                         help='If you check this option you can choose to automaticly get e-mailed when the backup to the external server failed.')
    email_to_notify = fields.Char('E-mail to notify',
                                  help='Fill in the e-mail where you want to be notified that the backup failed on the FTP.')

    # Columns fro Google Drive
    is_upload = fields.Boolean('Upload to Google Drive',
                               help="If you check this option you can specify the details needed to upload to google drive.")
    drive_folder_id = fields.Char(string='Folder ID',
                                  help="make a folder on drive in which you want to upload files; then open that folder; the last thing in present url will be folder id")
    gdrive_email_notif_ids = fields.Many2many('res.users', string="Person to Notify")
    drive_autoremove = fields.Boolean('Auto. Remove Uploaded Backups',
                                      help='If you check this option you can choose to automaticly remove the backup after xx days')

    drive_to_remove = fields.Integer('Remove after x days',
                                     help="Choose after how many days the backup should be deleted. For example:\nIf you fill in 5 the backups will be removed after 5 days.",
                                    )

    @api.depends('google_drive_authorization_code')
    def _compute_drive_uri(self):
        google_drive_uri = self.env['google.service']._get_google_token_uri('drive', scope=self.env[
            'google.drive.config'].get_google_scope())
        for config in self:
            config.google_drive_uri = google_drive_uri

    def set_values(self):
        params = self.env['ir.config_parameter'].sudo()
        authorization_code_before = params.get_param('google_drive_authorization_code')
        super(DbBackup, self).set_values()
        authorization_code = self.google_drive_authorization_code
        refresh_token = False
        if authorization_code and authorization_code != authorization_code_before:
            refresh_token = self.env['google.service'].generate_refresh_token('drive', authorization_code)
        params.set_param('google_drive_refresh_token', refresh_token)

    
    @api.constrains('name')
    def _check_db_exist(self):
        self.ensure_one()

        db_list = self.get_db_list(self.host, self.port)
        if self.name in db_list:
            return True
        raise ValidationError(_('Error ! No such database exists!'))
        return False

    # _constraints = [(_check_db_exist, _('Error ! No such database exists!'), [])]

    @api.multi
    def test_sftp_connection(self, context=None):
        self.ensure_one()

        # Check if there is a success or fail and write messages
        messageTitle = ""
        messageContent = ""
        error = ""
        has_failed = False

        for rec in self:
            db_list = self.get_db_list(rec.host, rec.port)
            pathToWriteTo = rec.sftp_path
            ipHost = rec.sftp_host
            portHost = rec.sftp_port
            usernameLogin = rec.sftp_user
            passwordLogin = rec.sftp_password

            # Connect with external server over SFTP, so we know sure that everything works.
            try:
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(ipHost, portHost, usernameLogin, passwordLogin, timeout=10)
                sftp = s.open_sftp()
                messageTitle = _("Connection Test Succeeded!\nEverything seems properly set up for FTP back-ups!")
            except Exception as e:
                _logger.critical('There was a problem connecting to the remote ftp: ' + str(e))
                error += str(e)
                has_failed = True
                messageTitle = _("Connection Test Failed!")
                if len(rec.sftp_host) < 8:
                    messageContent += "\nYour IP address seems to be too short.\n"
                messageContent += _("Here is what we got instead:\n")
            finally:
                if s:
                    s.close()

        if has_failed:
            raise Warning(messageTitle + '\n\n' + messageContent + "%s" % str(error))
        else:
            raise Warning(messageTitle + '\n\n' + messageContent)

    @api.model
    def schedule_backup(self):
        conf_ids = self.search([])
        if conf_ids:

            for rec in conf_ids:
                db_list = self.get_db_list(rec.host, rec.port)

                if rec.name in db_list:
                    try:
                        if not os.path.isdir(rec.folder):
                            os.makedirs(rec.folder)
                    except:
                        raise ValidationError(_('The backup path does not exist, and Odoo does not have permission to create the path, please create the path manually or choose another path.'))
                    # Create name for dumpfile.
                    try:
                        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz)
                    except:
                        raise ValidationError(_('Please select the user time zone from the preferences'))

                    date_today = pytz.utc.localize(datetime.datetime.today()).astimezone(user_tz)
                    bkp_file = '%s_%s.%s' % (rec.name,date_today.strftime('%Y-%m-%d_%H_%M_%S'), rec.backup_type)

                    file_path = os.path.join(rec.folder, bkp_file)
                    uri = 'http://' + rec.host + ':' + rec.port
                    conn = xmlrpclib.ServerProxy(uri + '/xmlrpc/db')
                    bkp = ''
                    try:
                        # try to backup database and write it away
                        fp = open(file_path, 'wb')
                        odoo.service.db.dump_db(rec.name, fp, rec.backup_type)
                        fp.close()
                        self.return_warning(rec.folder)

                    except Exception as error:
                        _logger.debug(
                            "Couldn't backup database %s. Bad database administrator password for server running at http://%s:%s" % (
                            rec.name, rec.host, rec.port))
                        _logger.debug("Exact error from the exception: " + str(error))
                        continue

                else:
                    _logger.debug("database %s doesn't exist on http://%s:%s" % (rec.name, rec.host, rec.port))

                self.google_drive_upload(rec, file_path, bkp_file)

                # Check if user wants to write to SFTP or not.
                if rec.sftp_write is True:
                    try:
                        # Store all values in variables
                        dir = rec.folder
                        pathToWriteTo = rec.sftp_path
                        ipHost = rec.sftp_host
                        portHost = rec.sftp_port
                        usernameLogin = rec.sftp_user
                        passwordLogin = rec.sftp_password
                        _logger.debug('sftp remote path: %s' % pathToWriteTo)

                        try:
                            s = paramiko.SSHClient()
                            s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            s.connect(ipHost, portHost, usernameLogin, passwordLogin, timeout=20)
                            sftp = s.open_sftp()
                        except Exception as error:
                            _logger.critical('Error connecting to remote server! Error: ' + str(error))

                        try:
                            sftp.chdir(pathToWriteTo)
                        except IOError:
                            # Create directory and subdirs if they do not exist.
                            currentDir = ''
                            for dirElement in pathToWriteTo.split('/'):
                                currentDir += dirElement + '/'
                                try:
                                    sftp.chdir(currentDir)
                                except:
                                    _logger.info('(Part of the) path didn\'t exist. Creating it now at ' + currentDir)
                                    # Make directory and then navigate into it
                                    sftp.mkdir(currentDir, 777)
                                    sftp.chdir(currentDir)
                                    pass
                        sftp.chdir(pathToWriteTo)
                        # Loop over all files in the directory.
                        for f in os.listdir(dir):
                            if rec.name in f:
                                fullpath = os.path.join(dir, f)
                                if os.path.isfile(fullpath):
                                    try:
                                        sftp.stat(os.path.join(pathToWriteTo, f))
                                        _logger.debug(
                                            'File %s already exists on the remote FTP Server ------ skipped' % fullpath)
                                    # This means the file does not exist (remote) yet!
                                    except IOError:
                                        try:
                                            # sftp.put(fullpath, pathToWriteTo)
                                            sftp.put(fullpath, os.path.join(pathToWriteTo, f))
                                            _logger.info('Copying File % s------ success' % fullpath)
                                        except Exception as err:
                                            _logger.critical(
                                                'We couldn\'t write the file to the remote server. Error: ' + str(err))

                        # Navigate in to the correct folder.
                        sftp.chdir(pathToWriteTo)

                        _logger.debug("Checking expired files")
                        # Loop over all files in the directory from the back-ups.
                        # We will check the creation date of every back-up.
                        for file in sftp.listdir(pathToWriteTo):
                            if rec.name in file:
                                # Get the full path
                                fullpath = os.path.join(pathToWriteTo, file)
                                # Get the timestamp from the file on the external server
                                timestamp = sftp.stat(fullpath).st_mtime
                                createtime = datetime.datetime.fromtimestamp(timestamp)
                                now = datetime.datetime.now()
                                delta = now - createtime
                                # If the file is older than the days_to_keep_sftp (the days to keep that the user filled in on the Odoo form it will be removed.
                                if delta.days >= rec.days_to_keep_sftp:
                                    # Only delete files, no directories!
                                    if stat.S_ISREG(sftp.stat(fullpath).st_mode) and (".dump" in file or '.zip' in file):
                                        _logger.info("Delete too old file from SFTP servers: " + file)
                                        sftp.unlink(file)
                        # Close the SFTP session.
                        sftp.close()
                        s.close()
                    except Exception as e:
                        try:
                            sftp.close()
                            s.close()
                        except:
                            pass
                        _logger.error('Exception! We couldn\'t back up to the FTP server. Here is what we got back instead: %s' % str(e))
                        # At this point the SFTP backup failed. We will now check if the user wants
                        # an e-mail notification about this.
                        if rec.send_mail_sftp_fail:
                            try:
                                ir_mail_server = self.env['ir.mail_server']
                                message = "Dear,\n\nThe backup for the server " + rec.host + " (IP: " + rec.sftp_host + ") failed.Please check the following details:\n\nIP address SFTP server: " + rec.sftp_host + "\nUsername: " + rec.sftp_user + "\nPassword: " + rec.sftp_password + "\n\nError details: " + tools.ustr(
                                    e) + "\n\nWith kind regards"
                                msg = ir_mail_server.build_email("advance_advance_auto_backup@" + rec.name + ".com", [rec.email_to_notify],
                                                                "Backup from " + rec.host + "(" + rec.sftp_host + ") failed",
                                                                message)
                                ir_mail_server.send_email(self._cr, self._uid, msg)
                            except Exception:
                                pass

                """
                Remove all old files (on local server) in case this is configured..
                """
                if rec.autoremove:
                    dir = rec.folder
                    # Loop over all files in the directory.
                    for f in os.listdir(dir):
                        fullpath = os.path.join(dir, f)
                        # Only delete the ones wich are from the current database
                        # (Makes it possible to save different databases in the same folder)
                        if rec.name in fullpath:
                            timestamp = os.stat(fullpath).st_ctime
                            createtime = datetime.datetime.fromtimestamp(timestamp)
                            now = datetime.datetime.now()
                            delta = now - createtime
                            if delta.days >= rec.days_to_keep:
                                # Only delete files (which are .dump and .zip), no directories.
                                if os.path.isfile(fullpath) and (".dump" in f or '.zip' in f):
                                    _logger.info("Delete local out-of-date file: " + fullpath)
                                    os.remove(fullpath)
        else:
            raise ValidationError(_('Plz., Complete the backup settings. From: Settings - Backup - Configure back-ups. or contact the system administrator'))



    @api.multi
    def google_drive_upload(self, rec, file_path, bkp_file):
        g_drive = self.env['google.drive.config']
        access_token = GoogleDrive.get_access_token(g_drive)
        # GOOGLE DRIVE UPLOAP
        if rec.is_upload:
            headers = {"Authorization": "Bearer %s" % (access_token)}
            para = {
                "name": "%s" % (str(bkp_file)),
                "parents": ["%s" % (str(rec.drive_folder_id))]
            }
            files = {
                'data': ('metadata', json.dumps(para), 'application/json; charset=UTF-8'),
                'file': open("%s" % (str(file_path)), "rb")
            }
            r = requests.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers=headers,
                files=files
            )

            # SENDING EMAIL NOTIFICATION
            try:
                if r.status_code == 200:
                    email_to = ""
                    for record in rec.gdrive_email_notif_ids.mapped('login'):
                        email_to += record + ','

                    notification_template = self.env['ir.model.data'].sudo().get_object('advance_auto_backup',
                                                                                        'email_google_drive_upload')
                    values = notification_template.generate_email(self.id)
                    values['email_from'] = self.env['res.users'].browse(self.env.uid).company_id.email
                    values['email_to'] = email_to
                    values['subject'] = "Google Drive Upload Successful"
                    values['body_html'] = "<h3>Backup Successfully Uploaded!</h3>" \
                                        "Please see below details. <br/> <br/> " \
                                        "<b>Backup File: %s" % (str(bkp_file)) + \
                                        " <a href='https://drive.google.com/drive/u/0/folders/%s'>Open</a></b>" % (
                                            str(rec.drive_folder_id))
                    
                    send_mail = self.env['mail.mail'].create(values)
                    send_mail.send(True)
                else:
                    response = r.json()
                    code = response['error']['code']
                    message = response['error']['errors'][0]['message']
                    reason = response['error']['errors'][0]['reason']

                    email_to = ""
                    for rec in rec.gdrive_email_notif_ids.mapped('login'):
                        email_to += rec + ','

                    notification_template = self.env['ir.model.data'].sudo().get_object('advance_auto_backup',
                                                                                        'email_google_drive_upload')
                    values = notification_template.generate_email(self.id)
                    values['email_from'] = self.env['res.users'].browse(self.env.uid).company_id.email
                    values['email_to'] = email_to
                    values['subject'] = "Google Drive Upload Failed"
                    values['body_html'] = "<h3>Backup Upload Failed!</h3>" \
                                        "Please see below details. <br/> <br/> " \
                                        "<table style='width:100%'>" \
                                        "<tr> " \
                                        "<th align='left'>Backup</th>" \
                                        "<td>" + (str(bkp_file)) + "</td></tr>" \
                                                                    "<tr> " \
                                                                    "<th align='left'>Code</th>" \
                                                                    "<td>" + str(code) + "</td>" \
                                                                                        "</tr>" \
                                                                                        "<tr>" \
                                                                                        "<th align='left'>Message</th>" \
                                                                                        "<td>" + str(
                        message) + "</td>" \
                                "</tr>" \
                                "<tr>" \
                                "<th align='left'>Reason</th>" \
                                "<td>" + str(reason) + "</td>" \
                                                        "</tr> " \
                                                        "</table>"

                    send_mail = self.env['mail.mail'].create(values)
                    send_mail.send(True)
            except:
                raise ValidationError(_('Backup done!\n But Odoo did not send a notice to the e-mail, There is an error in the email settings or the person receiving the notification is using Odoo to Handle the Notification from Email Preferences'))

        # AUTO REMOVE UPLOADED FILE

        if rec.drive_autoremove and res.drive_to_remove:
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
            params = {
                'access_token': access_token,
                'q': "mimeType='application/%s'" % (rec.backup_type),
                # 'q': "mimeType='application/zip'",
                'fields': "nextPageToken,files(id,name, createdTime, modifiedTime, mimeType)"
            }
            url = "/drive/v3/files"
            status, content, ask_time = self.env['google.service']._do_request(url, params, headers, type='GET')

            for item in content['files']:
                date_today = datetime.datetime.today().date()
                create_date = datetime.datetime.strptime(str(item['createdTime'])[0:10], '%Y-%m-%d').date()

                delta = date_today - create_date
                if delta.days >= rec.drive_to_remove:
                    params = {
                        'access_token': access_token
                    }
                    url = "/drive/v3/files/%s" % (item['id'])
                    response = self.env['google.service']._do_request(url, params, headers, type='DELETE')
        
    def return_warning(self, file_path):
        message = _("Congratulations: the backup has completed successfully. In the path: %s") % file_path
        self.env['bus.bus'].sendone((self._cr.dbname, 'res.partner',self.env.user.partner_id.id),{
            'type': 'user_connection',
            'title': _('Backup is Done'),
            'message': message,
            'sticky': True,
            'success': True,
            'error_message': False,
            'warning_message': False
            })



class Ir_Cron(models.Model):
    _inherit = 'ir.cron'

    field_domain= fields.Boolean()

    @api.onchange('field_domain')
    def onchange_field_domain(self):
        self.model_id = self.env['ir.model'].search([('model','=','db.backup')]) if self.field_domain else None
        
    