# -*- coding: utf-8 -*-
{
    'name': "Float discount for sale, bill, order & invoice lines",

    'summary': """
        Adds option to set float discount value for order, sale, bill and invoice lines.""",

    'description': """
        In addition to the percentage discount, you can now add its value directly. It's simple, fast and easy.
        Works for lines in quotations, orders, invoices and vendor bills.
    """,

    'author': "wattanadev",
    'website': "http://thaiodoo.com/",


    'category': 'Sales',
    'version': '12.0.1.0.0',
    'license': 'LGPL-3',
    'support': '',
    'images': ['images/main_screenshot.png'],

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'sale_management'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}