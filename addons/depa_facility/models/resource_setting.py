from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from PIL import Image
import base64
import imagehash
import io
import hashlib

class resource_setting(models.Model):
    _name = 'resource_setting'


    resource_name = fields.Text(
        string='ชื่อพาหนะ',
        required=True,
    )
    resource_license = fields.Text(
        string='ทะเบียน',
        required=True,
    )
    resource_capacity = fields.Char(
        string='ความจุ',
        required=True,
    )
    resource_driver = fields.Text(
        string='คนขับ',
        required=True,
    )
    resource_phone = fields.Text(
        string='เบอร์โทรศัพท์',
        required=True,
    )
    resource_type = fields.Selection(
        [
            ('van', 'รถตู้'),
            ('car', 'รถยนต์'),
        ],
        default='van',
        string='ประเภทรถ',
        required=True
    )
    resource_img = fields.Binary(
        string='รูป'
    )

    def name_get(self):
        return [(rec.id, rec.resource_name) for rec in self]

