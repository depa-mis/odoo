from odoo import models, fields, api, _

class SaleInherit(models.Model):
    _inherit = 'sale.order'

    test_name = fields.Char()

class SaleOrderOptionInherit(models.Model):
    _inherit = 'sale.order.option'

    is_new_option = fields.Boolean()

class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    def order_line_click(self):
        self.product_uom_qty += 1

