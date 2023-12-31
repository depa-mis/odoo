{
    'name': 'BiOne_Account_Form',
    'version': '12.0.1.0.0',
    'author': 'BiOne',
    'license': 'AGPL-3',
    'website': 'https://bione.co.th',
    'category': 'Report',
    'depends': [
        'web',
        'account',
        'sale_stock',
        'l10n_th_withholding_tax_cert_form',
    ],
    'data': [
        'data/paper_format_delivery_order_tax_invoice_B.xml',
        'data/paper_format.xml',
        'data/report_data.xml',
        'reports/account_style.xml',
        'reports/billing_form.xml',
        'reports/credit_note_tax_invoice_form.xml',
        'reports/debit_note_tax_invoice_form.xml',
        'reports/delivery_order_form.xml',
        'reports/delivery_order_tax_invoice_A_form.xml',
        'reports/delivery_order_tax_invoice_B_form.xml',
        'reports/payment_request_form.xml',
        'reports/receipt_form.xml',
        'reports/wht_cert_layout.xml',
    ],
    'installable': True,
}
