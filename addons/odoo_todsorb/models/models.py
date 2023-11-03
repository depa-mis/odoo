# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class odoo_todsorb(models.Model):
    _name = 'odoo_todsorb.odoo_todsorb'

    name = fields.Char(
        string='First name'
    )
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)
    description = fields.Text()
    odoo_todsorb_reference_id = fields.Many2one(
        'odoo_todsorb_reference',
    )
    odoo_todsorb_reference_id_description = fields.Text(
        related='odoo_todsorb_reference_id.description',
    )
    odoo_todsorb_reference_ids = fields.Many2many(
        'odoo_todsorb_reference',
    )
    odoo_todsorb_reference_ids_2 = fields.Many2many(
        'odoo_todsorb_reference',
    )

    unit_price = fields.Float()
    qty = fields.Integer()
    price_total = fields.Float(compute='_compute_price_total')

    @api.onchange('odoo_todsorb_reference_id')
    def _onchange_ref_id(self):
        self.unit_price += self.odoo_todsorb_reference_id.value

    @api.depends('unit_price', 'qty')
    def _compute_price_total(self):
        self.price_total = self.unit_price * self.qty

    @api.constrains('qty')
    def _constrains_qty(self):
        if self.qty <= 0:
            raise ValidationError(_('Qty must greater than zero'))

    @api.depends('value')
    def _value_pc(self):
        self.value2 = float(self.value) / 100

    def create(self, vals):
        return super(odoo_todsorb, self).create(vals)

    def write(self, vals):
        return super(odoo_todsorb, self).write(vals)


class odooTodsorbReference(models.Model):
    _name = 'odoo_todsorb_reference'

    name = fields.Char()
    value = fields.Integer(
        default=1
    )
    description = fields.Text()
    active = fields.Boolean(default=True)

    @api.multi
    def name_get(self):
        return [(cat.id, cat.name + ' ' + str(cat.value) + '-' + str(cat.description)) for cat in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            ref_ids = self._search(args + [
                '|',
                ('name', 'like', name),
                ('description', 'ilike', name),
            ], limit=limit)
        else:
            ref_ids = self._search(args, limit=limit)
        return self.browse(ref_ids).name_get()
