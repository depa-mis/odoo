# -*- coding: utf-8 -*-
{
    'name': "depa_contract",

    'summary': """
        List of contractor with depa""",

    'description': """
        List of contractor with depa
    """,

    'author': "MIS - depa",
    'website': "https://www.depa.or.th",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Contract',
    'version': '1.0.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'web',
        'mail',
        'pfb_saraban',
        'pfb_saraban_addons'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/depa_contract_views.xml',
        # 'views/leave_request_types_views.xml',
        # 'views/leave_request_public_holidays_views.xml',
        # 'views/leave_setting_employee_views.xml',
        # 'views/leave_request_state_views.xml',
        # 'views/leave_overview_views.xml',
        # 'views/leave_request_approve_views.xml',
        # 'views/leave_summary_views.xml',
        # 'views/leave_summary_approver_views.xml',
        # 'wizards/views/leave_request_reject_wizard.xml',
        # 'wizards/views/leave_request_cancel_approved_wizard.xml',
        # 'data/leave_state.xml',
        # 'data/leave_types.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        # 'demo/demo.xml',
    ],
}