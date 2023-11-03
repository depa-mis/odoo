# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta
from datetime import datetime, date
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from PIL import Image
import base64
import io
import hashlib

class kpi_setting_pm_inherit(models.Model):
    _inherit = 'kpi_pm_lines'

    kpi_id = fields.Char(
        compute='_compute_kpi',
        string='KPI ID',
    )

    kpi_name = fields.Char(
        compute='_compute_kpi',
        string='KPI NAME',
    )

    # project_plan = 

    # kpi_type = fields.Char(
    #     compute='',
    #     string='KPI TYPE',
    #     store=True
    # )
    fiscal_year = fields.Char(
        compute='_compute_kpi',
        string='ปีงบประมาณ',
    )

    @api.depends("kpi_pm_lines_id")
    def _compute_kpi(self):
        for rec in self:
            if rec.kpi_pm_lines_id:
                department_line = rec.env['kpi_setting_dsm_department_lines'].browse(
                int(rec.kpi_pm_lines_id))
                # department_line = self.kpi_setting_dsm_department_lines_id
                rec.kpi_id = department_line.kpi_code
                rec.kpi_name = department_line.kpi_name

                kpi_dept = self.env['kpi_setting_dsm_department'].search([
                    ('id', '=', department_line.kpi_setting_department_lines_id.id),
                ], limit=1)
                if kpi_dept:
                    fiscal_year_obj = self.env['fw_pfb_fin_system_fiscal_year'].search([
                        ('id', '=', kpi_dept.fiscal_year.id),
                    ], limit=1)
                    if fiscal_year_obj:
                        rec.fiscal_year = fiscal_year_obj.fiscal_year
