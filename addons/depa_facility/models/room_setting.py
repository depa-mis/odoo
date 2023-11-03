from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from PIL import Image
import base64
import imagehash
import io
import hashlib

class room_setting(models.Model):
    _name = 'room_setting'


    room_name = fields.Text(
        string='ชื่อห้องประชุม',
        required=True,
    )
    room_capacity = fields.Char(
        string='ความจุ',
        required=True,
    )
    room_floor = fields.Selection(
        [
            ('1', '1'),
            ('2', '2'),
            ('3', '3'),
            ('4', '4'),
            ('5', '5'),
            ('6', '6'),
            ('7', '7'),
            ('8', '8'),
        ],
        string="ชั้น",
        required=True,
    )
    is_approve = fields.Boolean(
        string="ต้องผ่านการอนุมัติ",
        default=False,
    )
    room_img = fields.Binary(
        string='รูป'
    )

    def name_get(self):
        return [(rec.id, rec.room_name) for rec in self]

