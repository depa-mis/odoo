# -*- coding: utf-8 -*-
from odoo import http

class OdooTodsorb(http.Controller):
    @http.route('/odoo_todsorb/odoo_todsorb/', auth='public')
    def index(self, **kw):
        return "Hello, world"

    @http.route('/odoo_todsorb/odoo_todsorb/objects/', auth='public')
    def list(self, **kw):
        return http.request.render('odoo_todsorb.listing', {
            'root': '/odoo_todsorb/odoo_todsorb',
            'objects': http.request.env['odoo_todsorb.odoo_todsorb'].search([]),
        })

    @http.route('/odoo_todsorb/odoo_todsorb/objects/<model("odoo_todsorb.odoo_todsorb"):obj>/', auth='public')
    def object(self, obj, **kw):
        return http.request.render('odoo_todsorb.object', {
            'object': obj
        })