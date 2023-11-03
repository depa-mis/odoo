# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    test_name = fields.Char()


class SaleOrderOptionInherit(models.Model):
    _inherit = 'sale.order.option'

    test_name = fields.Char()


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    def increment_quantity(self):
        self.product_uom_qty += 1