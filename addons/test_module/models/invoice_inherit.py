from odoo import models, fields, api, _

class invoice_inherit(models.Model):
    _inherit = 'account.invoice'
    sale_test = fields.Char()

    def add_tax_value(self):
        self.amount_total_signed += (self.amount_total_signed * 0.07)

class invoice_line_inherit(models.Model):
    _inherit = 'account.invoice.line'
    is_cash = fields.Boolean()

    def invoice_line_click(self):
        self.quantity += 1


