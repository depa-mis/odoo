# -*- coding: utf-8 -*-
{
    'name': "FIN System dashboard sample",

    'summary': """
        Financial System Dashboard""",

    'description': """
    """,

    'author': "Zephyr",
    'website': "https://www.perfect.in.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '12.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'fin_system'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/restrict.xml',
        'views/fin_system_100_dashboard.xml',
        'views/fin_system_100_menu.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}
