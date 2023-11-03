# -*- coding: utf-8 -*-
{
    'name': "depa_kpi_record",

    'summary': """
        Record KPI of each Employee in depa
        """,

    'description': """
        Record KPI of each Employee in depa
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
        'hr',
        'depa_tmi'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/kpi_record_project_views.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}