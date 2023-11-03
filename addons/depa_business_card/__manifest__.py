# -*- coding: utf-8 -*-
{
    'name': "depa_business_card",

    'summary': """
        For Business Card using in depa
        """,

    'description': """
        For Business Card using in depa
    """,

    'author': "MIS - depa",
    'website': "http://www.depa.or.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'vCard',
    'version': '1.0.5',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/business_card_views.xml',
        'views/business_category_views.xml',
        'views/business_card_lines_views.xml',
        'wizards/views/business_card_make_cancel_wizard.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}