# -*- coding: utf-8 -*-
{
    'name': "depa_facility",

    'summary': """
        For Facility using in depa
        """,

    'description': """
        For Facility using in depa
    """,

    'author': "MIS - depa",
    'website': "http://www.depa.or.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'fin_system'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/depa_facility_group.xml',
        # 'views/postal_system_views.xml',
        # 'views/postal_system_setting_views.xml',
        # 'views/postal_system_approve_views.xml',
        'views/resource_setting_views.xml',
        'views/resource_book_views.xml',
        'views/resource_book_approve_views.xml',
        'views/room_setting_views.xml',
        'views/room_book_views.xml',
        'views/room_book_approve_views.xml',
        'report/address_label_template.xml',
        'report/report.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}