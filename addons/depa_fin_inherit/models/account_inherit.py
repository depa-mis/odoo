from datetime import date
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _


class account_inherit(models.Model):
    _inherit = 'account.invoice'

    code_ref = fields.Char(
        string="เลขที่ใบเสร็จ",
    )

class fin_201_button_inherit(models.Model):
    _inherit = 'fw_pfb_fin_system_201'

    fin_approved = fields.Boolean(
        default=False
    )

    # change fin_audit to true
    def approve_fin_audit(self):
        if self.state == 'completed':
            self.ensure_one()
            self.update({
                'fin_audit': True,
                'fin_approved': True
            })