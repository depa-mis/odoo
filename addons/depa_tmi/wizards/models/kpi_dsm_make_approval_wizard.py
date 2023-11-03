from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date

class kpi_dsm_make_approval_wizard(models.TransientModel):
    _name = 'kpi_dsm_make_approval_wizard'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    kpi_setting_dsm_id = fields.Many2one(
        'kpi_setting_dsm'
    )

    remark = fields.Text(
        string="ความคิดเห็น",
        help="กรอกเพื่อแสดงความคิดเห็น",
        required=True
    )

    current_state = fields.Char(
        string="สถานะ",
    )

    def action_approve(self):
        setting_dsm_id = self.kpi_setting_dsm_id
        approval_lines_count = len(setting_dsm_id.kpi_setting_dsm_approval_lines_ids)

        for line in setting_dsm_id.kpi_setting_dsm_lines_ids:
            if not line.is_validated:
                raise ValidationError(_('คุณต้องตรวจข้อมูล KPI ครบทุกรายการก่อนทำการอนุมัติ'))

        # Is last approval
        if setting_dsm_id.approve_count < approval_lines_count:
            setting_dsm_id.kpi_setting_dsm_approval_lines_ids[approval_lines_count - 1].update({
                'approve_datetime': datetime.today(),
                'remark': self.remark,
                'status': 'done'
            })
            setting_dsm_id.update({
                'current_approval_id': False,
                'state': 'completed',
            })
            setting_dsm_id.approve_count += 1

        elif setting_dsm_id.approve_count == approval_lines_count:
            setting_dsm_id.kpi_setting_dsm_approval_lines_ids[approval_lines_count-1].update({
                'approve_datetime': datetime.today(),
                'remark': self.remark,
                'status': 'done'
            })
            setting_dsm_id.update({
                'current_approval_id': False,
                'state': 'completed',
            })
            self.kpi_setting_dsm_id.message_post(body="ขออนุมัติ KPI(ติดตาม) เสร็จสิ้น")

            # create kpi into each group
            groups = self.env['hr.department'].search([
                ('department_level', '=', 'DL3')
            ])
            for group in groups:
                group_setting_lines = []
                manager_id = group.manager_id.id
                group_lines = self.env['kpi_group_lines'].search([
                    ('kpi_group_lines_id.kpi_setting_dsm_lines_id.id', '=', setting_dsm_id.id),
                    ('kpi_group_department_id', '=', group.id),
                ])
                if group_lines:
                    fin = 0.0
                    cus = 0.0
                    inter = 0.0
                    learn = 0.0
                    for group_line in group_lines:
                        rec = group_line.kpi_group_lines_id
                        if rec.kpi_bsc == 'F':
                            fin += rec.kpi_weight
                            self.financial = fin
                        elif rec.kpi_bsc == 'C':
                            cus += rec.kpi_weight
                            self.customer = cus
                        elif rec.kpi_bsc == 'I':
                            inter += rec.kpi_weight
                            self.internal = inter
                        else:
                            learn += rec.kpi_weight
                            self.learning = learn

                        group_setting_lines.append((
                            0,
                            0,
                            {
                                'kpi_setting_dsm_lines_id': rec.id,
                                'kpi_code': rec.kpi_code,
                                'kpi_name': rec.kpi_name,
                                'kpi_weight': group_line.kpi_group_weight,
                                # 'kpi_target': rec.kpi_target,
                                # 'kpi_unit': rec.kpi_unit.id,
                                'kpi_bsc': rec.kpi_bsc,
                                'kpi_budget': rec.kpi_budget,
                                'kpi_calculate': rec.kpi_calculate,
                                'kpi_definition': rec.kpi_definition,
                                'kpi_has_assistant': group_line.kpi_has_assistant,
                                'kpi_assistant_employee_id': group_line.kpi_assistant_employee_id.id,
                                'kpi_status': 'pending',
                                'kpi_group_definition_lines_ids': [(6, 0, group_line.kpi_group_definition_line_ids.ids)]
                            }
                        ))

                    self.env['kpi_setting_dsm_group'].create({
                        'department_id': group.id,
                        'financial': fin,
                        'customer': cus,
                        'internal': inter,
                        'learning': learn,
                        'kpi_setting_group_lines_ids' : group_setting_lines,
                        'kpi_setting_group_approval_lines_ids': [(0, 0, {
                            'employee_id': manager_id,
                            'status': 'pending'
                        })],
                    })


    def action_adjustment(self):
        # print(self)
        setting_dsm_id = self.kpi_setting_dsm_id
        approval_lines_count = len(setting_dsm_id.kpi_setting_dsm_approval_lines_ids)
        setting_dsm_id.kpi_setting_dsm_approval_lines_ids[approval_lines_count - 1].update({
            'approve_datetime': datetime.today(),
            'remark': self.remark,
            'status': 'adjust'
        })
        setting_dsm_id.update({
            'current_approval_id': False,
            'state': 'adjust',
        })
        setting_dsm_id.approve_count = 0

    def action_reject(self):
        setting_dsm_id = self.kpi_setting_dsm_id
        approval_lines_count = len(setting_dsm_id.kpi_setting_dsm_approval_lines_ids)
        setting_dsm_id.kpi_setting_dsm_approval_lines_ids[approval_lines_count - 1].update({
            'approve_datetime': datetime.today(),
            'remark': self.remark,
            'status': 'reject'
        })
        setting_dsm_id.update({
            'current_approval_id': False,
            'state': 'rejected',
        })
        self.kpi_setting_dsm_group_id.message_post(body="ขออนุมัติ KPI(ติดตาม) ปรับแก้ไข")