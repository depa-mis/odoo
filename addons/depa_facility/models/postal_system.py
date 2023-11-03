# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
import smtplib

POSTAGE_TYPES = [
    ('register', 'ลงทะเบียน'),
    ('ems', 'EMS'),
    ('parcel', 'พัสดุ'),
    ('regular', 'ธรรมดา')
]

class postal_system(models.Model):
    _name = 'postal_system'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_employee_id(self):
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self._uid)
        ], limit=1)
        return employee.id

    object_send = fields.Char(
        string='สิ่งที่ต้องการส่ง',
        required=True,
        track_visibility='onchange'
    )

    postal_serial = fields.Char(
        string = 'รหัส',
        copy = False,
        track_visibility = 'onchange',
        store = True
    )

    requester_id = fields.Many2one(
        "hr.employee",
        string='ผู้ยื่นคำร้อง',
        default= lambda self: self._get_employee_id()
    )

    recipient_name = fields.Char(
        string='ผู้รับ',
        required=True,
        track_visibility='onchange',
        default=False
    )

    destination = fields.Text(
        string='ปลายทาง',
        required=True,
        track_visibility='onchange',
        default=False
    )

    destination_type_selection = fields.Selection(
        [
            ('internal', 'ในประเทศ'),
            ('external', 'ต่างประเทศ')
        ],
        string="ประเภทปลายทาง",
        default='internal',
        required=True
    )

    destination_country = fields.Many2one(
        "postal_destination_country",
        string='ปลายทาง (ประเทศ)',
        copy=False,
        default=False
    )

    destination_province = fields.Many2one(
        "postal_destination_province",
        string='ปลายทาง (จังหวัด)',
        copy=False,
        default=False
    )

    destination_postal_code = fields.Char(
        string='รหัสไปรษณีย์',
        required=True,
        default=False
    )
    
    destination_preset = fields.Many2one(
        "postal_destination_preset",
        string='ปลายทางที่ตั้งค่าไว้',
        copy=False,
        default=False
    )

    sticker_serial = fields.Char(
        string='เลขสติ๊กเกอร์',
        default=False,
        copy=False,
        track_visibility='onchange'
    )

    postal_type = fields.Selection(
        string='ประเภทการส่ง',
        selection=POSTAGE_TYPES,
        required=True,
        track_visibility='onchange'
    )

    remark = fields.Text(
        string='หมายเหตุ'
    )

    approve_date = fields.Datetime(
        string='วันที่อนุมัติ',
        default=False,
        track_visibility='onchange'
    )

    @api.onchange('destination_type_selection')
    def _change_destination_type_selection(self):
        for rec in self:
            if rec.destination_type_selection == 'internal':
                rec.destination_country = False
            elif rec.destination_type_selection == 'external':
                rec.destination_province = False
                rec.destination_preset = False

    @api.onchange('destination_preset')
    def _change_destination_preset(self):
        for rec in self:
            if rec.destination_preset:
                rec.destination = rec.destination_preset.destination_detail
                rec.destination_postal_code = rec.destination_preset.destination_postal_code
                rec.destination_province = rec.destination_preset.destination_province.id
                rec.destination_type_selection = 'internal'

    @api.multi
    def write(self, vals):
        if vals.get('sticker_serial') and not self.approve_date:
            vals['approve_date'] = datetime.now()
        res = super(postal_system, self).write(vals)
        return res

    def send_postal_request(self):
        for rec in self:
            sequence_id = rec.env['ir.sequence'].search([
                ('code', '=', 'postal')
            ]) or False
            if sequence_id:
                nextnumber = sequence_id.next_by_id()
                rec.update({
                    'postal_serial': nextnumber
                })
            else:
                raise ValidationError(
                        _('Please add the sequence'))

    def print_complete_document(self):
        return self.env.ref('depa_facility.report_address_label').report_action(self)


class postal_destination_province(models.Model):
    _name = 'postal_destination_province'

    name = fields.Char(
        string='จังหวัด',
        required=True
    )

    postal_id = fields.One2many(
        "postal_system",
        "destination_province"
    )



class postal_destination_country(models.Model):
    _name = 'postal_destination_country'

    name = fields.Char(
        string='ประเทศ',
        required=True
    )

    postal_id = fields.One2many(
        "postal_system",
        "destination_country"
    )

class postal_destination_preset(models.Model):
    _name = 'postal_destination_preset'

    name = fields.Char(
        string='สถานที่ปลายทาง',
        required=True
    )

    postal_id = fields.One2many(
        "postal_system",
        "destination_preset"
    )

    destination_detail = fields.Text(
        required=True
    )

    destination_province = fields.Many2one(
        "postal_destination_province",
        string='จังหวัด',
        required=True
    )

    destination_postal_code = fields.Char(
        required=True
    )