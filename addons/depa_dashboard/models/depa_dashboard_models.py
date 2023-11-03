# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from pytz import timezone
import smtplib
from odoo.http import request
from requests import get

class depa_dashboard(models.Model):
    _name = 'depa_dashboard'

    request_desc = fields.Text(
        string="รายละเอียด",
        required=True
    )
    

