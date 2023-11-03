from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class fin_inherit_reset_button(models.Model):
    _inherit = 'fw_pfb_fin_system_100'

    recent_reset_count = fields.Integer(
        default=0,
        copy=False
    )

    @api.onchange('recent_reset_count')
    def _notification_reset_recent(self):
        return {
            'warning': {
                'title': 'แจ้งเตือนผู้ใช้งาน',
                'message': 'เปลี่ยนสถานะของแถวอนุมัติล่าสุดเรียบร้อยแล้ว'}
        }

    def action_reset_recent_approve(self):
        #TODO: ต้องดูว่าขั้นตอนก่อนหน้า มีกี่คน
        #TODO: ต้องเปลี่ยน waiting_line_ids ให้ด้วย
        #TODO: ต้องสร้าง waiting line ตัวใหม่เด้อ
        APPROVE_STEPS = {
            '1': 'DirectorOfDepartment',
            '2': 'RelatedGroup',
            '3': 'DirectorOfFinance',
            '4': 'AssistantOfOffice',
            '5': 'DeputyOfOffice',
            '6': 'SmallNote',
            '7': 'DirectorOfOffice',
            '8': 'completed'
        }
        recent_lines = self.env['fw_pfb_fin_system_100_approver'].search([
            ('fin_id', '=', self.id),
            ('state', '=', 'approve'),
            ('approval_type', '=', 'mandatory')
        ])
        if len(recent_lines) >= 1:
            recent_line = recent_lines[-1]
            #setting_line_ids = []
            all_recent_lines = self.env['fw_pfb_fin_system_100_approver'].search([
                ('fin_id', '=', self.id),
                ('state', '=', 'approve'),
                ('approval_type', '=', 'mandatory'),
                ('approve_step', '=', recent_line.approve_step)
            ])
            #for line in all_recent_lines:
                #self.env['waiting.fin.system.100.line'].search([
                #    ('fin_id', '=', self.id),
                #    ('approval_step', '=', recent_line.approve_step)
                #])
                
            raise ValidationError(all_waiting_lines)            #recent_line.update({
            #    'action_date': False,
            #    'memo': False,
            #    'state': 'pending'
            #})
            #reset_count = self.recent_reset_count + 1
            #self.update({
            #    'state': APPROVE_STEPS[str(recent_line.approve_step)],
            #    'recent_reset_count': reset_count
            #})
            #self.message_post(
            #    body=f"เปลี่ยนสถานะของ<br/>แถวอนุมัติที่: <b>{recent_line.position_index}</b><br/>บุคลากร: <b>{recent_line.employee_id.name}</b>    เป็น 'รอดำเนินการ' แล้ว"
            #)
        else:
            raise ValidationError("ยังไม่มีแถวที่ถูกอนุมัติแล้ว")