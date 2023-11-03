# -*- coding: utf-8 -*-
{
    'name': "depa_fin_inherit",

    'summary': """
        For inherit Fin module
        """,

    'description': """
        For inherit Fin module
    """,

    'author': "MIS - depa",
    'website': "http://www.depa.or.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'fin_system',
        'account',
        'analytic',
        'fin_system_extension'
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/fin_201_button_inherit_group.xml',
        'security/fin_inherit_reset_button_group.xml',
        'views/account_inherit_views.xml',
        'views/fin_201_button_inherit_views.xml',
        'views/fin_inherit_reset_button_views.xml',
        'views/account_analytic_account_views.xml',
        'wizard/wizard_fin_purchase_approval_views.xml'
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}