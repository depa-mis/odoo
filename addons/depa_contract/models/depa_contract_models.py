# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from pytz import timezone
from odoo.http import request
from requests import get

class depa_contract(models.Model):
    _name = 'depa_contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string="ชื่อ-นามสกุล",
        required=True,
    )

    contract_line_ids = fields.One2many(
        'depa_contract_lines',
        'contract_id',
        copy=False
    )

    company = fields.Char(
        string="ชื่อบริษัท"
    )

    email = fields.Char(
        string="อีเมล"
    )

    user_id = fields.Many2one(
        "res.users",
        string="ผู้ใช้งานที่เกี่ยวข้อง"
    )

    cad_password = fields.Text(
        string="CAD Password"
    )

    certificate_file = fields.Many2many(
        "ir.attachment",
        "contract_certificate_file_attachment_rel",
        "contract_certificate_file_attachment_rel",
        "ir_attachment_id",
        string='ไฟล์ .p12',
    )

    sign_img = fields.Binary(
        string="signature"
    )

class depa_contract_lines(models.Model):
    _name = "depa_contract_lines"

    is_active = fields.Boolean(
        string="เปิดใช้งาน",
        default=True
    )

    contract_id = fields.Many2one(
        'depa_contract',
        string="ชื่อผู้ทำสัญญา",
        ondelete='cascade'
    )

    contract_approval_lines_id = fields.Many2one(
        'document.internal.main',
        string="ผู้อนุมัติสัญญา",
        ondelete='cascade'
    )

    approved_date = fields.Datetime(
        string="วันเวลา อนุมัติ"
    )

    status = fields.Selection(
        [
            ("0", "รออนุมัติ"),
            ("1", "อนุมัติแล้ว"),
            ("2", "รับทราบแล้ว"),
            ("3", "ปฏิเสธแล้ว"),
        ],
        string="สถานะ",
        default="0"
    )