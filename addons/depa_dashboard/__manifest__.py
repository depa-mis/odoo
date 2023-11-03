# -*- coding: utf-8 -*-
{
    'name': "depa_dashboard",

    'summary': """
        depa dashbooard
    """,

    'description': """
        depa dashbooard
    """,

    'author': "MIS - depa",
    'website': "https://www.depa.or.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'fin_system'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        #'views/views.xml',
        'views/depa_dashboard_views.xml',
        'views/depa_dashboard_fin_views.xml'

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}