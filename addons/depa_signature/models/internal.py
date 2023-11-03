from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
# from odoo.add_ons.pfb_saraban.internal import internalDocument
from datetime import timedelta, datetime, date
import logging
from lxml import etree
import json
import base64
from io import BytesIO
from docx import Document
from docx.shared import Inches
import requests as r

_logger = logging.getLogger(__name__)


class internalDocumentInherit(models.Model):
    _inherit = 'document.internal.main'

    doc_pdf_signed = fields.Many2many(
        'ir.attachment',
        "attachment_document_internal_main_signed_rel",
        "document_internal_main_id",
        "attachment_id",
        string='Digital Signature File'
    )
    preview_attachment_id = fields.Many2one(
        'ir.attachment',
        'Preview Attachment'
    )
    head_officer_digital_signed = fields.Boolean(
        default=False,
        copy=False
    )
    file_for_signature = fields.Binary(
        string="D-Signature File",
        copy=False,
        track_visibility='onchange'
    )
    file_name_for_signature = fields.Char(
        string="D-Signature File",
        copy=False,
        track_visibility='onchange'
    )
    template = fields.Html(
        string="Template",
        default="<button class='btn btn-info btn-sm'><a style='color: white' href='https://short.depa.or.th/templateSignature' target='_blank'>ดาวน์โหลดตัวอย่างไฟล์</a></button>",
        required=False,
        copy=True
    )
    suffix = fields.Text(
        copy=True
    )
    circular_letter_check = fields.Boolean(
        string="หนังสือเวียน",
        default=False,
        copy=False
    )
    invitation_lines_ids = fields.One2many(
        'invitation_lines',
        'invitation_lines_id',
        copy=False
    )
    
    contract_approve = fields.Boolean(
        string="ขออนุมัติสัญญา",
        default=False,
        copy=False
    )

    contract_approval_lines_ids = fields.One2many(
        'depa_contract_lines',
        'contract_approval_lines_id',
        copy=False
    )

    specific_document_no = fields.Char(
        default=False
    )
    specific_date = fields.Date(
        default=False
    )

    docx_for_facility_signature = fields.Binary(
        string="ไฟล์ประกาศ สำหรับประกาศพัสดุ",
        copy=False,
        track_visibility='onchange'
    )

    docx_name_for_facility_signature = fields.Char(
        string="ไฟล์ประกาศ สำหรับประกาศพัสดุ",
        copy=False,
        track_visibility='onchange'
    )

    file_for_invitation_names = fields.Binary(
        string="ไฟล์รายชื่อแจ้งท้าย",
        copy=False,
        track_visibility='onchange'
    )

    file_name_for_invitation_names = fields.Char(
        string="ไฟล์รายชื่อแจ้งท้าย",
        copy=False,
        track_visibility='onchange'
    )

    file_for_facility_signature = fields.Binary(
        string="ไฟล์ใบแจ้งผล สำหรับประกาศพัสดุ",
        copy=False,
        track_visibility='onchange'
    )
    
    file_name_for_facility_signature = fields.Char(
        string="ไฟล์ใบแจ้งผล สำหรับประกาศพัสดุ",
        copy=False,
        track_visibility='onchange'
    )

    def action_preview_document(self):
        doc_id = self.id
        convert_status, data_encoded = self.env['make.approval.wizard'].convert_document(
            self.env['saraban_form'].from_data(doc_id)
        )
        if not convert_status:
            raise ValidationError(_('เกิดข้อผิดพลาดในการแสดงตัวอย่างเอกสาร'))

        attach_vals = {
            'name': '%s.pdf' % ('Document Pdf Preview'),
            'datas': data_encoded,
            'datas_fname': '%s.pdf' % ('Document Pdf Preview'),
        }

        attach_id = self.env['ir.attachment'].create(attach_vals)

        if self.preview_attachment_id:
            try:
                self.preview_attachment_id.unlink()
            except:
                pass
        self.write({'preview_attachment_id': attach_id.id})
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/%s?download=true' % (attach_id.id),
            'target': 'current',
        }

    def action_download_signed_document(self):
        if len(self.doc_pdf_signed) == 0:
            raise ValidationError(_('เกิดข้อผิดพลาดในการดาวน์โหลดเอกสารลงนาม'))

        doc_signed = self.doc_pdf_signed[0]
        self.env['download_document_signed_logging'].create({
            'signed_attachment_id': doc_signed.id,
            'user_id': self.env.uid,
            'ip_address': request.httprequest.environ['REMOTE_ADDR']
        })
        return {
            'type': 'ir.actions.act_url',
            'url': 'web/content/%s?download=true' % (doc_signed.id),
            'target': 'current',
        }

    def download_preview_pdf(self):
        url = "https://api.depa.or.th/wordtopdf2"
        file_name = "preview_document.docx"
        data_base64 = False
        docx_file = self.file_for_signature
        if docx_file:
            binary_file = base64.b64decode(docx_file)
            action = {"docxFile": (file_name, binary_file)}
            resp = r.post(url, files=action)

            if resp.status_code == 200:
                json_data = json.loads(resp.text)
                data_base64 = json_data['base64']
                attach_vals = {
                    'name': '%s.pdf' % ('Document Pdf Preview'),
                    'datas': data_base64,
                    'datas_fname': '%s.pdf' % ('Document Pdf Preview'),
                }
                attach_id = self.env['ir.attachment'].create(attach_vals)

                if self.preview_attachment_id:
                    try:
                        self.preview_attachment_id.unlink()
                    except:
                        pass

                self.write({'preview_attachment_id': attach_id.id})

                return {
                    'type': 'ir.actions.act_url',
                    'url': 'web/content/%s?download=true' % (attach_id.id),
                    'target': 'current',
                }
        else:
            raise ValidationError(_("ยังไม่มีการอัพโหลด D-signature File"))

    def send_email(self, action):
        if action == "contract":
            web_base = "https://contract.depa.or.th/sign/"
            for line in self.contract_approval_lines_ids:
                if str(line.status) == '0':
                    contractor = self.env['depa_contract'].browse(int(line.contract_id))
                    email_to = contractor.email
                    message_body = f"""
                    <html>
                        <head></head>
                        <body>
                            <p>
                                หนังสือสัญญา: {self.name} <br/>
                                เรื่อง: {self.subject} <br/>
                            </p>
                            ตรวจสอบได้ที่ <a href={web_base}{self.id}>ระบบลงนามสัญญา</a>
                        </body>
                    </html>
                    """
                    subject = f"แจ้งเตือนระบบลงนามสัญญา depa - Contract"
                    template_obj = request.env['mail.mail']
                    template_data = {
                        'subject': subject,
                        'body_html': message_body,
                        'email_from': request.env.user.company_id.email,
                        'email_to': email_to
                    }
                    template_id = template_obj.create(template_data)
                    template_id.send()

    def action_sent_to_supervisor(self):
        approval_lines = self.env['document.internal.main.setting.line'].search(
            [
                ('setting_id', '=', int(self.id)),
                ('contract_approve', '=', True)
            ],
        )
        if len(approval_lines) > 2:
            raise ValidationError("ผู้อนุมัติสัญญาต้องมี 2 ท่านเท่านั้น")
        name_amount = len(self.invitation_lines_ids)
        if name_amount > 0 and not self.circular_letter_check:
            raise ValidationError("ในกรณีที่มีรายชื่อแจ้งท้ายตั้งแต่ 1 รายชื่อขึ้นไป\nกรุณาเลือก หนังสือเวียน ก่อนส่งหนังสือ")
        if self.circular_letter_check and len(self.invitation_lines_ids) == 0:
            raise ValidationError("ในกรณีที่เลือกหนังสือเวียน\nกรุณาใส่รายชื่อแจ้งท้ายอย่างน้อย 1 รายชื่อ")
        if self.contract_approve and len(self.contract_approval_lines_ids) > 0:
            self.send_email(action="contract")
        res = super(internalDocumentInherit, self).action_sent_to_supervisor()
        return res
    
    @api.onchange('invitation_lines_ids')
    def change_invitation_name(self):
        name_amount = len(self.invitation_lines_ids)
        if name_amount > 5:
            raise ValidationError("ไม่สามารถเพิ่มรายชื่อแจ้งท้ายมากกว่า 5 รายชื่อได้" \
                                "\nเพื่อความเสถียรในการใช้งานระบบ" \
                                "\nหากมีรายชื่อเพิ่มเติมกรุณาแนบไฟล์ที่ 'ไฟล์รายชื่อแจ้งท้าย' (.xlsx) มาด้วย" \
                                "(ส่วนที่แนบไฟล์อยู่ที่ด้านล่างของ D-Signature File)"
                                )

    @api.multi
    def unlink(self):
        if not self.env.user.has_group('depa_signature.group_user_digital_signature_setting'):
            raise ValidationError("ไม่สามารถลบบันทึกข้อความ/หนังสือลงนามนี้ได้")
        return models.Model.unlink(self)

    def buttonClearNameReal(self):
        if self.name_real != "":
            self.update({
                'name_real': False,
            })

    @api.multi
    def action_make_approval_wizard(self):
        res = super(internalDocumentInherit, self).action_make_approval_wizard()
        if self.contract_approve:
            contract_approval_count = len(self.env['depa_contract_lines'].search([
                ('status', '=', '1'),
                ('contract_approval_lines_id', '=', self.id)
            ]))
            contract_count = len(self.env['depa_contract_lines'].search([
                ('contract_approval_lines_id', '=', self.id)
            ]))
            if int(contract_approval_count) != int(contract_count):
                raise ValidationError(f"กรุณารอให้ผู้ทำสัญญา อนุมัติจนครบทุกท่านก่อน\n(เหลืออีก \
                                    {(contract_count - contract_approval_count)} ท่าน)")
        return res

    def get_user_status(self, user_job_level):
        JOB_LEVEL = {
            "L1": 1,
            "L2": 1,
            "L3": 1,
            "L4": 1,
            "L5": 1,
            "L6": 1,
            "L7": 1,
            "L8": 4,
            "L9": 5,
            "L10": 7
        }
        return str(JOB_LEVEL[user_job_level])

    def make_hierarchy_order_line(self):
        self.ensure_one()
        self.update({
            'setting_line_ids': False
        })

        values = []
        employee_ids = []
        user = self.env.uid

        while True:
            current_user = self.env['hr.employee'].search([
                ('user_id', '=', user)
            ])
            if current_user.parent_id:
                current_parent = self.env['hr.employee'].browse(current_user.parent_id.id)
                employee_ids.append(current_parent.id)
                values.append([0, 0, {
                    'employee_id': current_parent.id,
                    'job_id_name': current_parent.job_id.id,
                    'status': self.get_user_status(current_parent.depa_job_level),
                    'step': self.get_user_status(current_parent.depa_job_level),
                    'approve_type': 'require',
                    'is_active': True
                }])
                user = current_parent.user_id.id
            else:
                break
        self.update({
            'setting_line_ids': values,
            'empolyee_name': [(6, _, employee_ids)],
        })

class DownloadDocumentSignedLogging(models.Model):
    _name = 'download_document_signed_logging'

    signed_attachment_id = fields.Many2one(
        'ir.attachment'
    )
    user_id = fields.Many2one(
        'res.users'
    )
    ip_address = fields.Char(
        string='IP Address'
    )


class InvitationList(models.Model):
    _name = 'invitation_lines'

    invitation_name = fields.Char(
        required=True,
        string="ชื่อ/ตำแหน่งผู้แจ้งท้าย"
    )

    invitation_lines_id = fields.Many2one(
        'document.internal_main',
        string='ผู้แจ้งท้าย',
        ondelete='cascade'
    )

    document_pdf_id = fields.Integer(
        default=0,
    )

    # file = fields.Binary(
    #     string="หนังสือเวียน",
    #     copy=False,
    # )
    # file_names = fields.Char(
    #     copy=False,
    # )

    def buttonDownload(self):
        # if self.invitation_lines_id:
        #     if self.invitation_lines_id.state != 'Done':
        if self.document_pdf_id != 0:
            return {
                'type': 'ir.actions.act_url',
                'url': 'web/content/%s?download=true' % (self.document_pdf_id),
                'target': 'current',
            }
        else:
            raise ValidationError(_('ไม่พบการลงนามสำหรับเอกสารเวียนของบุคคลนี้'))

class DocumentInternalMainSettingLineContract(models.Model):
    _inherit = 'document.internal.main.setting.line'

    contract_approve = fields.Boolean(
        string="อนุมัติสัญญา",
        default=False
    )