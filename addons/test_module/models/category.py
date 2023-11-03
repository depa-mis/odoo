from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class categoty(models.Model):
    _name = "test_module.category"

    desc = fields.Char()
    active = fields.Boolean(default=True)


    @api.multi
    def name_get(self):
        return [(cat.id, cat.desc) for i, cat in enumerate(self)]

    @api.model
    def name_search(self, name, args=None, operator='like', limit=100):
        if not args:
            args = []
        if name:
            result = self._search(args + [
                ('desc', operator, name),
            ])
        else:
            result = self._search(args, limit=limit)
        # print(result)
        return self.browse(result).name_get()

    @api.constrains('desc')
    def check_desc(self):
        print(self)
        if not self.desc:
            raise UserError(_("กรุณากรอกข้อมูลด้วย"))