# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class test_module(models.Model):
    _name = 'test_module.test_module'

    name = fields.Char()
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)
    position = fields.Char()
    status = fields.Integer(default=1, string="สถานะ")
    description = fields.Text()
    test_relation_id = fields.Many2one("test_relation.test_relation")
    test_relation_ids = fields.Many2many(
        "test_relation.test_relation",
        "test_module_test_relation_rel",
        "test_module_id",
        "test_relation_id"
    )
    test_relations = fields.Many2many("test_relation.test_relation")
    unit_price = fields.Float()
    quantity = fields.Integer()
    price = fields.Float(compute="_price_pc", store=True)
    sale_inherit_id = fields.Many2one("sale.order")
    remark = fields.Char()


    @api.depends('value')
    def _value_pc(self):
        self.value2 = float(self.value) / 100

    @api.depends('unit_price', 'quantity')
    def _price_pc(self):
        self.price = self.unit_price * self.quantity

    @api.onchange('test_relation_id')
    def _test_relation_id_change(self):
        # print(self)
        self.price += self.test_relation_id.price

    @api.constrains('quantity')
    def _quantity_cs(self):
        if self.quantity < 0:
            raise ValidationError(_("Quantity ห้ามน้อยกว่า 0"))

    # @api.onchange('sale_inherit_id')
    # def _sale_inherit_id_change(self):
    #     # print(self)
    #     self.quantity = self.sale_inherit_id.order_line[0].product_uom_qty
    #     self.unit_price = self.sale_inherit_id.order_line[0].price_unit
    #     self.price = self.sale_inherit_id.order_line[0].price_total

    @api.model
    def create(self, val):
        vars = super(test_module, self).create(val)
        print(vars.id)
        return vars

    @api.multi
    def write(self, val):
        print(val)
        return super(test_module, self).write(val)

class test_relation(models.Model):
    _name = 'test_relation.test_relation'
    # _rec_name = "relation"

    relation = fields.Char()
    status = fields.Integer(default=1, string="สถานะ")
    desc = fields.Char()
    active = fields.Boolean(default=True)
    price = fields.Float(default=100)
    category_id = fields.Many2one("test_module.category")
    category_ids = fields.Many2many("test_module.category")
    category_ids_key = fields.Many2many(
        "test_module.category",
        "test_relation_category_rel",
        "test_relation_id",
        "category_id"
    )
    total = fields.Integer(readonly=True)


    @api.multi
    def name_get(self):
        return [(relate.id, relate.relation) for i, relate in enumerate(self)]

    @api.model
    def name_search(self, name, args=None, operator='like', limit=100):
        if not args:
            args = []
        if name:
            result = self._search(args + [
                '|',
                ('relation', operator, name),
                ('desc', operator, name),
            ])
        else:
            result = self._search(args, limit=limit)
        print(result)
        return self.browse(result).name_get()

    @api.onchange('category_id')
    def category_id_change(self):
        # print(self)
        self.total += 10