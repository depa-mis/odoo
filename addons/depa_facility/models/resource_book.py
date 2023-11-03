from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
import requests as r
from pythainlp.util import thai_strftime

STATES = [
    ('draft', 'ฉบับร่าง'),
    ('pending', 'รออนุมัติ'),
    ('completed', 'เสร็จสิ้น'),
    ('rejected', 'ปฏิเสธ')
]
class resource_book(models.Model):
    _name = 'resource_book'

    def _get_employee_info(self):
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self._uid)
        ])
        return employee


    resource_book_state = fields.Selection(
        STATES,
        string="สถานะ",
        default="draft"
    )
    resource_book_type = fields.Selection(
        [
            ('van', 'รถตู้'),
            ('car', 'รถยนต์'),
        ],
        default='van',
        string='ประเภทรถ',
        required=True
    )
    resource_book_user = fields.Char(
        string='ชื่อ-นามสกุล',
        readonly=True,
        default=lambda self: self._get_employee_info().name
    )

    resource_book_start = fields.Datetime(
        string='ตั้งแต่วันที่',
        required=True,
        default=lambda self: datetime.now(),
    )
    resource_book_sdate = fields.Char(
        string='วันทีเริ่ม',
        required=True,
    )
    resource_book_stime = fields.Char(
        string='เวลาเริ่ม',
        required=True,
    )
    resource_book_end = fields.Datetime(
        string='ถึงวันที่',
        required=True,
        default=lambda self: datetime.now(),
    )
    resource_book_edate = fields.Char(
        string='วันที่สิ้นสุด',
        required=True,
    )
    resource_book_etime = fields.Char(
        string='เวลาสิ้นสุด',
        required=True,
    )
    resource_book_desc = fields.Text(
        string='รายละเอียด',
        required=True
    )
    resource_book_head = fields.Many2one(
        "hr.employee",
        string='ผู้มอบหมาย',
        copy=False,
        # required=True
    )
    resource_book_source = fields.Text(
        string='สถานที่ต้นทาง',
        required=True
    )
    resource_book_destination = fields.Text(
        string='สถานที่ปลายทาง',
        required=True
    )
    resource_book_wait = fields.Selection(
        [
            ('no', 'ไม่ต้องรอกลับ'),
            ('wait', 'รอกลับ'),
        ],
        default='no',
        string='การเดินทางกลับ',
        required=True
    )
    resource_book_waittime = fields.Float(
        string='เวลา',
    )

    resource_book_car = fields.Many2one(
        "resource_setting",
        string="เลือกพาหนะ",
        required=True
    )
    resource_book_user_ids = fields.One2many(
        "resource_book_user",
        "resource_book_user_id"
    )
    no_ce = fields.Html(
        string='no_create_edit',
        sanitize=False,
        compute='_compute_no_ce_css',
        store=False,
    )

    using_car_ids = fields.Many2many(
        'resource_setting'
    )

    @api.onchange('resource_book_start', 'resource_book_end', 'resource_book_type')
    def _onchange_resource_book_start(self):
        start = self.resource_book_start
        end = self.resource_book_end
        sdate = self.resource_book_sdate
        stime = self.resource_book_stime
        car_type = self.resource_book_type
        
        # dt = start.strftime('%Y-%m-%d %H:%M:%S')
        self.resource_book_sdate = start.strftime('%Y-%m-%d')
        self.resource_book_stime = (start + timedelta(hours=7)).strftime('%H:%M')
        self.resource_book_edate = end.strftime('%Y-%m-%d')
        self.resource_book_etime = (end + timedelta(hours=7)).strftime('%H:%M')

        resource_using = self.env['resource_book'].search([
            ('resource_book_start', '<=', end),
            ('resource_book_end', '>=', start),
            ('resource_book_state', '=', 'completed'),
            ('resource_book_type', '=', car_type)
        ])

        if resource_using:
            car_using = []
            for car in resource_using:
                car_using.append(car.resource_book_car.id)

            if car_using:
                self.using_car_ids = [(6, 0, car_using)]
        else:
            self.using_car_ids = False

        if self.resource_book_start > self.resource_book_end:
            self.resource_book_end = self.resource_book_start


    def send_resource_request(self):
        if self.resource_book_state == 'draft':
            self.update({
                'resource_book_state': 'pending',
            })
    def send_resource_approve(self):
        if self.resource_book_state == 'pending':
            self.update({
                'resource_book_state': 'completed',
            })
        token = 'M4RjZU3WhlFlSvNFj2ZHsZjUBf35dORKbcnNP5OoWML'
        headers = {'content-type': 'application/x-www-form-urlencoded',
                   'Authorization': 'Bearer ' + token}
        url = 'https://notify-api.line.me/api/notify'

        start = thai_strftime(self.resource_book_start, "%d %B %y")
        stime= self.resource_book_start.strftime('%H:%M')
        end = thai_strftime(self.resource_book_end, "%d %B %y")
        etime = self.resource_book_end.strftime('%H:%M')

        message_body = self.resource_book_car.resource_name + '\n' + 'วันที่ ' + start + ' เวลา ' + stime + ' น.' \
                       + ' - ' + end + ' เวลา '+ etime + ' น. ' + '\n' + 'ผู้จอง ' + self.resource_book_user \
                       + '\n' + 'เดินทางจาก ' + self.resource_book_source + ' - ' + self.resource_book_destination
        # print(message_body)
        r.post(url, headers=headers, data={'message': message_body})
    def send_resource_reject(self):
        if self.resource_book_state == 'pending':
            self.update({
                'resource_book_state': 'rejected',
            })

    @api.depends('resource_book_state')
    def _compute_no_ce_css(self):
        for application in self:
            if application.resource_book_state != 'draft':
                    application.no_ce = '<style>.o_form_button_create {display: none !important;}</style>' \
                                        '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                application.no_ce = False

class resource_book_user(models.Model):
    _name = 'resource_book_user'

    resource_book_user_id = fields.Many2one(
        "resource_book",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="ผู้ร่วมเดินทาง",
    )
    job_id = fields.Many2one(
        'hr.job',
        string="ตำแหน่ง",
        compute="_depends_employee_id",
        store=True
    )

    @api.depends('employee_id')
    def _depends_employee_id(self):
        for rec in self:
            rec.job_id = rec.employee_id.job_id.id




