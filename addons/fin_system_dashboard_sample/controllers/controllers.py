# -*- coding: utf-8 -*-
from odoo import http, api, tools
from odoo.http import request
import json 

class FinSystem(http.Controller):
    @http.route('/fin_system_dashboard/', auth='public', website=True)
    def index(self, **kw):
        employee_id = http.request.env['hr.employee'].search([
                    ('user_id', '=', request.uid)
                ])
        if not employee_id:
            return request.render('fin_system_dashboard_sample.restrict_area')

        render_values = {}

        fin_100_list = http.request.env['fw_pfb_fin_system_100'].search([
                ('state', '!=', 'draft')
            ])
        fin_list = {}
        i = 0
        if fin_100_list:
            for fin100 in fin_100_list:
                fin_list[i] = {
                            'fin100_name': fin100.fin_no,
                            'fin100_state': fin100.state
                        }
                i += 1

        render_values = {
                    'fin_list': fin_list
                }
        
        return request.render("fin_system_dashboard_sample.fin_100_dashboard", render_values)

    # @http.route('/fin_system/fin_system/objects/', auth='public')
    # def list(self, **kw):
    #     return http.request.render('fin_system.listing', {
    #         'root': '/fin_system/fin_system',
    #         'objects': http.request.env['fin_system.fin_system'].search([]),
    #     })
    #
    # @http.route('/fin_system/fin_system/objects/<model("fin_system.fin_system"):obj>/', auth='public')
    # def object(self, obj, **kw):
    #     return http.request.render('fin_system.object', {
    #         'object': obj
    #     })
