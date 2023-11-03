# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

{
    'name': 'PFB DEPA Voucher Qweb',
    'version': '12.0.1.0.1',
    'author': 'PP',
    'license': 'AGPL-3',
    'website': '',
    'category': 'Report',
    'depends': ['base',
                'web',
                'bione_thai_account',
                ],

    'data': [
        'security/ir.model.access.csv',
        'data/paper_format.xml',
        'reports/payment_voucher.xml',
        'data/report_data.xml',
    ],
    'installable': True,
}
