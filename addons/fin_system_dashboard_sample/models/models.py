# -*- coding: utf-8 -*-
from odoo import api, fields, models


class FinSystem100Dashboard(models.Model):
    _name = 'fin.system.100.dashboard.sample'

    dashboard = fields.Char(string='Mock up text')

