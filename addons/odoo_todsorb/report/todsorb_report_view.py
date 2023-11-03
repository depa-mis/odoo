# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT


class OdooTodsorbReportWizard(models.TransientModel):
    _name = 'todsorb_report_wizard'

    name_code = fields.Char()

    @api.multi
    def get_report(self):
        """Call when button 'Get Report' clicked.
        """
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'name_code': self.name_code,
            },
        }

        return self.env.ref('odoo_todsorb.seat_reservation_report').report_action(self, data=data)


class OdooTodsorb(models.AbstractModel):

    _name = 'report.odoo_todsorb.odoo_todsorb_report_view'

    @api.model
    def _get_report_values(self, docids, data=None):
        name_code = data['form']['name_code']

        docs = []
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'docs': docs,
            'name_code': name_code,
        }