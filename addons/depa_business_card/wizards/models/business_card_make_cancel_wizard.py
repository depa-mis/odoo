from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date

class business_card_make_cancel_wizard(models.TransientModel):
    _name = 'business_card_make_cancel_wizard'

    business_card_line_id = fields.Many2one(
        'business_card_lines'
    )


    remark = fields.Text(
        string="รายละเอียดการยกเลิก",
        help="กรอกเพื่อแสดงความคิดเห็น",
        required=True
    )


    def action_save_cancel(self):
        # print(self)


        cancel = self.env['business_card_make_cancel_wizard'].search([
            ('business_card_line_id', '=', self.business_card_line_id.id)
        ], order='id desc', limit=1)

        self.business_card_line_id.update({
            'memo_for_cancel': cancel.remark,
        })


        return {
            'type': 'ir.actions.act_window_close'
        }
        # raise ValidationError(_('Not your turn'))
