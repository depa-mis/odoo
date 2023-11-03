# -*- coding: utf-8 -*-
import base64
import json
from odoo import api, fields, models
from odoo import tools, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError
import requests

class depa_profile(models.Model):
    _inherit = 'hr.employee'

    employee_group_id = fields.Many2one(
        "depa_group",
        string="กลุ่มงาน",
        store=True,
        default=False
    )

    department_id_name = fields.Char(
        string="สังกัด",
        store=True,
        default=False
    )

    cad_password = fields.Text(
        string="Certificate Password"
    )

    certificate_file = fields.Many2many(
        "ir.attachment",
        "employee_certificate_file_attachment_rel",
        "employee_certificate_file_attachment_rel",
        "ir_attachment_id",
        string="ไฟล์ certificate (.p12)"
    )

    employee_job_history_ids = fields.One2many(
        "depa_employee_job_history",
        "employee_id",
        string="ประวัติการรับตำแหน่ง"
    )

    @api.depends('department_id')
    def _get_department_name(self):
        for rec in self:
            if rec.department_id:
                department = self.env['hr.department'].search([
                    ('id', '=', rec.department_id.id)
                ], limit=1)
                rec.department_id_name = department.name
                rec.employee_group_id = department.department_group_id

    def get_action_res_id(self):
        context = self._context
        current_uid = context.get('uid')
        employee = self.sudo().env['hr.employee'].search([
            ('user_id', '=', current_uid)
        ], limit=1)
        action = self.env.ref('depa_profile.depa_profile_window').read()[0]
        action['res_id'] = employee.id if employee.id else False
        return action
    
    @api.multi
    def write(self, values):
        if ("job_title" in values) and ("job_id" in values):
            data = {
                "name": values.get("job_title"),
                "job_id": values.get("job_id"),
                "employee_id": self.id,
                "appointed_date": datetime.today().strftime("%Y-%m-%d")
            }
            self.env['depa_employee_job_history'].create(data)
        return super(depa_profile, self).write(values)
    
    def create_signature_certificate(self):
        for rec in self:
            resp = requests.post(url="https://contract-api.depa.or.th/employee/certificate",
                                json={
                                    "user_id": rec._uid
                                })
            if resp.status_code == 200:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }
            else:
                raise ValidationError("ไม่สามารถสร้าง Signature Certificate ได้ในขณะนี้")
            
class EmployeeHistory(models.Model):
    _name = "depa_employee_job_history"

    name = fields.Char(
        string="ตำแหน่ง",
        required=True
    )

    employee_id = fields.Many2one("hr.employee")

    job_id = fields.Many2one("hr.job")

    appointed_date = fields.Date(string="วันที่รับตำแหน่ง")