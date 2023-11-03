# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class work_acceptance_inherit(models.Model):
    _inherit = 'work.acceptance'

    date_accept = fields.Datetime(
        string='Accepted Date',
        readonly=False,
    )
