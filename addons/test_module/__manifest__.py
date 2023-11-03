# -*- coding: utf-8 -*-
{
    'name': "test_module",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'sale_management', 'account'],

    # always loaded
    'data': [
        'security/group_test.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/relation_views.xml',
        'views/templates.xml',
        'views/sale_inherit.xml',
        'views/category_views.xml',
        'views/invoice_inherit_views.xml',
        'views/charts_views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}