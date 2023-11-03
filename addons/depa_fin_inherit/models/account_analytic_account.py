from odoo import _, api, fields, models

class AccountAnalyticAccountInherit(models.Model):
    _inherit = 'account.analytic.account'
    
    def active_analytic_account(self):
        for rec in self:
            if not(rec.active):
                rec.update({
                    'active': True,
                })
    
    def inactive_analytic_account(self):
        for rec in self:
            if rec.active:
                rec.update({
                    'active': False,
                })
    