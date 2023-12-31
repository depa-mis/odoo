# -*- coding: utf-8 -*-
{
    'name': 'BiOne Manual Currency Exchange Rate',
    'license':  "Other proprietary",
    'summary': """Manually set currency exchange rate on records.""",
    'description': """Grants users ability to manually set exchange rate on the following records.
                    Purchase Orders
                    Sale Orders
                    Invoices
                    Payments
                    """,
    'author': "Bi One Solutions",
    'website': "https://www.bione.co.th",
    'category': 'Accounting',
    'version': '12.0.1.1',
    "depends" : ['base','account','purchase', 'sale', 'sale_management','stock', 'purchase_stock', 'sale_stock'],
    'data': [
            "views/customer_invoice.xml",
            "views/account_payment_view.xml",
            "views/purchase_view.xml",
            "views/sale_view.xml",
             ],
    'images':  ["static/description/image.png"],
}
