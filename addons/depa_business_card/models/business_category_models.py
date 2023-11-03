from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from PIL import Image
import base64
import imagehash
import io
import hashlib

class business_category_models(models.Model):
    _name = 'business_category'


    category_name = fields.Char(
        string='หมวดหมู่',
        required=True,
    )


    def name_get(self):
        return [(rec.id, rec.category_name) for rec in self]

