from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError

class business_card_models(models.Model):
    _name = 'business_card'

    name = fields.Char(
        string="ชื่อหน่วยงาน/บริษัท",
        required=True,
    )
    address = fields.Text(
        string="ที่อยู่"
    )
    image = fields.Binary(
        string="ภาพ"
    )
    business_card_lines_ids = fields.One2many(
        'business_card_lines',
        'business_card_id',
        string="สมาชิก"
    )

class business_card_lines(models.Model):
    _name = 'business_card_lines'

    business_card_id = fields.Many2one(
        'business_card',
        string="Business Card id",
    )
    executive_position = fields.Selection(
        [
            (0, "CEO/President"),
            (1, "Executive"),
            (2, "Officer")
        ],
        string="ตำแหน่งบริหาร",
        default=2
    )
    step = fields.Integer(
        string="ลำดับ",
    )
    name = fields.Char(
        string="ชื่อ-นามสกุล(TH)",
        required=True,
    )
    name_en = fields.Char(
        string="ชื่อ-นามสกุล(EN)",
        required=True,
    )
    position = fields.Char(
        string="ตำแหน่ง",
        required=True
    )
    phone_number = fields.Text(
        string="เบอร์โทรศัพท์",
        # required=True
    )
    email = fields.Char(
        string="อีเมล"
    )
    remark = fields.Text(
        string="Note"
    )
    employees = fields.Many2many(
        'hr.employee',
        string="พนักงานที่ติดต่อ"
    )
    business_card_lines_history_ids = fields.One2many(
        'business_card_lines_history',
        'business_card_lines_id',
        string="ประวัติการรับตำแหน่ง"
    )
    user_image = fields.Binary(
        string="รูป"
    )
    memo_for_cancel = fields.Text(
        string="ยกเลิก"
    )

    @api.multi
    def write(self, values):
        memo_for_cancel = values.get("memo_for_cancel", self.memo_for_cancel)

        # cancel = self.env['business_card_make_cancel_wizard'].search([
        #     ('business_card_line_id', '=', self.id)
        # ], order='id desc', limit=1)

        data = {
            'name': self.name,
            'position': self.position,
            'phone_number': self.phone_number,
            'email': self.email,
            'business_card_lines_id': self.id,
            'memo_for_cancel': memo_for_cancel
        }

        res = super(business_card_lines, self).write(values)
        self.env['business_card_lines_history'].create(data)
        return res


    def action_make_cancel_wizard(self):
        # print(self)
        return {
            'name': "Make Cancel Wizard",
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'business_card_make_cancel_wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_business_card_line_id': self.id,

            }
        }

    def action_make_restore(self):
        # print(self.memo_for_cancel)
        if self.memo_for_cancel != True:
            self.update({
                'memo_for_cancel': False,
            })



class business_card_lines_history(models.Model):
    _name = 'business_card_lines_history'

    business_card_lines_id = fields.Many2one(
        'business_card_lines',
        string="Business Card Lines ID"
    )
    name = fields.Char(
        string="ชื่อ-นามสกุล"
    )
    position = fields.Char(
        string="ตำแหน่ง"
    )
    phone_number = fields.Char(
        string="เบอร์โทรศัพท์"
    )
    email = fields.Char(
        string="อีเมล"
    )
    memo_for_cancel = fields.Text(
        string="ยกเลิก"
    )