# -*- coding: utf-8 -*-
{
    'name': "depa_saraban_inherit",

    'summary': """
        For inherit Saraban module
        """,

    'description': """
        For inherit Saraban module
    """,

    'author': "MIS - depa",
    'website': "http://www.depa.or.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inherit',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'purchase_requisition',
        'purchase_work_acceptance'
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/receive_document_inherit_views.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}