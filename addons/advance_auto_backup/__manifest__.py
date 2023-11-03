# -*- coding: utf-8 -*-
{
    'name': "Automated Backups",

    'summary': 'Automated backups',

    'description': """The Automated Backups module enables the user to make configurations for the automatic backup of the database. Backups can be taken on the local system or on a remote server, through SFTP.
You only have to specify the hostname, port, backup location and databasename (all will be pre-filled by default with correct data.
If you want to write to an external server with SFTP you will need to provide the IP, username and password for the remote backups.
The base of this module is taken from Odoo SA V6.1 (https://www.odoo.com/apps/modules/6.0/auto_backup/), (https://apps.odoo.com/apps/modules/12.0/auto_backup/), (https://apps.odoo.com/apps/modules/12.0/auto_backup_upload/) and then upgraded and heavily expanded.
This module is made and provided by VanRoey.be nad Yenthe Van Ginneken.
Automatic backup for all such configured databases can then be scheduled as follows:  
                      
1) Go to Settings / Technical / Automation / Scheduled actions.
2) Search the action 'Backup scheduler'.
3) Set it active and choose how often you wish to take backups.
4) If you want to write backups to a remote location you should fill in the SFTP details.
""",

    'author': "Sonod",
    'website': "https://sonod.tech",
    'category': 'Administration',
    'version': '12.0.0.1',
    'installable': True,
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['mail'],

    # always loaded
    'data': [
        'security/user_groups.xml',
        'security/ir.model.access.csv',
        'views/backup_view.xml',
        'views/templates/auto_backup_mail_templates.xml',
        'data/backup_data.xml',
    ],
    'images': ['static/description/main_screenshot.jpg'],
    'live_test_url': 'https://www.youtube.com/watch?v=qxdZzalz-3w',

}
