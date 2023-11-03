# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class fw_pfb_FS100(models.Model):
    _inherit = 'fw_pfb_fin_system_100'

    @api.multi
    def fin_cancel(self):
        if self.approver:
            for rec in self.approver:
                rec.write({
                    'state': "",
                })
        self.write({
            'waiting_line_ids': [(6, 0, [])]
        })
        res = super(fw_pfb_FS100, self).fin_cancel()
        return res
