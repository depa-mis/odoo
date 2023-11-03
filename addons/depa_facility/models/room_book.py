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


class room_book(models.Model):
    _name = 'room_book'

    def _get_employee_info(self):
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self._uid)
        ])
        return employee

    room_book_state = fields.Selection(
        STATES,
        string="สถานะ",
        default="draft"
    )
    room_book_floor = fields.Selection(
        [
            ('1', '1'),
            ('2', '2'),
        ],
        default='2',
        string='ชั้น',
        required=True
    )
    room_book_user = fields.Char(
        string='ชื่อ-นามสกุล',
        readonly=True,
        default=lambda self: self._get_employee_info().name
    )

    room_book_start = fields.Datetime(
        string='ตั้งแต่วันที่',
        required=True,
        default=lambda self: datetime.now(),
    )
    room_book_startdate = fields.Char(
        string='วันทีเริ่ม',
        required=True,
    )
    room_book_enddate = fields.Char(
        string='ถึงวันที่',
        required=True,
    )
    # room_book_sdate = fields.Char(
    #     string='วันทีเริ่ม',
    #     required=True,
    # )
    # room_book_stime = fields.Char(
    #     string='เวลาเริ่ม',
    #     required=True,
    # )
    room_book_end = fields.Datetime(
        string='ถึงวันที่',
        required=True,
        default=lambda self: datetime.now(),
    )
    # room_book_edate = fields.Char(
    #     string='วันที่สิ้นสุด',
    #     required=True,
    # )
    # room_book_etime = fields.Char(
    #     string='เวลาสิ้นสุด',
    #     required=True,
    # )
    room_book_desc = fields.Text(
        string='รายละเอียด',
        required=True
    )
    resource_book_head = fields.Many2one(
        "hr.employee",
        string='ผู้มอบหมาย',
        copy=False,
        # required=True
    )
    room_booking = fields.Many2one(
        "room_setting",
        string="ห้องประชุม",
        required=True
    )
    room_book_invite_ids = fields.One2many(
        "room_book_invite",
        "room_book_invite_id"
    )
    no_ce = fields.Html(
        string='no_create_edit',
        sanitize=False,
        compute='_compute_no_ce_css',
        store=False,
    )

    using_room_ids = fields.Many2many(
        'room_setting'
    )

    @api.onchange('room_book_start', 'room_book_end', 'room_book_floor')
    def _onchange_room_book_start(self):
        start = self.room_book_start
        end = self.room_book_end
        floor = self.room_book_floor

        # img = self.env['room_setting'].search([])
        # for image in img:
        #     self.book_img = image.room_img
        #     print(image.room_img)

        # self.room_book_sdate = start.strftime('%Y-%m-%d')
        # self.room_book_stime = (start + timedelta(hours=7)).strftime('%H:%M')
        # self.room_book_edate = end.strftime('%Y-%m-%d')
        # self.room_book_etime = (end + timedelta(hours=7)).strftime('%H:%M')
        self.room_book_startdate = start.strftime('%Y-%m-%d') + ' ' + (start + timedelta(hours=7)).strftime('%H:%M')
        self.room_book_enddate = end.strftime('%Y-%m-%d') + ' ' + (end + timedelta(hours=7)).strftime('%H:%M')

        startdate = self.room_book_startdate
        enddate = self.room_book_enddate

        room_using = self.env['room_book'].search([
            ('room_book_startdate', '<', enddate),
            ('room_book_enddate', '>', startdate),
            ('room_book_state', '=', 'completed'),
            ('room_book_floor', '=', floor)
            # ('room_book_sdate', '<=', self.room_book_edate),
            # ('room_book_edate', '>=', self.room_book_sdate),
            # ('room_book_stime', '<', self.room_book_etime),
            # ('room_book_etime', '>', self.room_book_stime),
            # ('room_book_state', '=', 'completed'),
            # ('room_book_floor', '=', floor)
        ])
        if room_using:
            room_booking_using = []
            for room in room_using:
                room_booking_using.append(room.room_booking.id)

                if room_booking_using:
                    self.using_room_ids = [(6, 0, room_booking_using)]

        else:
            self.using_room_ids = False

        if self.room_book_start > self.room_book_end:
            self.room_book_end = self.room_book_start

    def send_room_request(self):
        if self.room_book_state == 'draft':
            if not self.room_booking.is_approve:
                self.update({
                    'room_book_state': 'completed',
                })
            if self.room_booking.is_approve:
                self.update({
                    'room_book_state': 'pending',
                })
                # M4RjZU3WhlFlSvNFj2ZHsZjUBf35dORKbcnNP5OoWML
                token = '6DaMVhmJuLaAqLmsvsPYNggV0A7FHKeZnKtxiN4dDc4'
                headers = {'content-type': 'application/x-www-form-urlencoded',
                           'Authorization': 'Bearer ' + token}
                url = 'https://notify-api.line.me/api/notify'

                start = thai_strftime(self.room_book_start, "%d %B %y")
                stime = self.room_book_start.strftime('%H:%M')
                end = thai_strftime(self.room_book_end, "%d %B %y")
                etime = self.room_book_end.strftime('%H:%M')

                message_body = 'ห้องประชุม : ' + self.room_booking.room_name + '\n' + 'วันที่ ' + start + ' เวลา ' + stime + ' น.' \
                               + ' - ' + end + ' เวลา ' + etime + ' น. ' + '\n' + 'ผู้จอง ' + self.room_book_user
                # print(message_body)
                r.post(url, headers=headers,
                       data={'message': message_body, 'stickerPackageId': '789', 'stickerId': '10856'})

    def send_room_approve(self):
        if self.room_book_state == 'pending':
            self.update({
                'room_book_state': 'completed',
            })


    def send_room_reject(self):
        if self.room_book_state == 'pending':
            self.update({
                'room_book_state': 'rejected',
            })

    @api.depends('room_book_state')
    def _compute_no_ce_css(self):
        for application in self:
            if application.room_book_state != 'draft':
                application.no_ce = '<style>.o_form_button_create {display: none !important;}</style>' \
                                    '<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                application.no_ce = False



class room_book_invite(models.Model):
    _name = 'room_book_invite'

    room_book_invite_id = fields.Many2one(
        "room_book",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="ผู้เข้าร่วมประชุม",
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





