from odoo import api, models
from bahttext import bahttext


class InvoiceSaleForm(models.AbstractModel):
    _name = 'report.invoice_sale_qweb.invoice_sale_pdf_report_pdf'

    @api.multi
    def _get_report_values(self, docids, data=None):
        docs = self.env['account.invoice'].browse(docids)
        thaibahttext = ''
        for doc in docs:

            thaibahttext = bahttext(doc.amount_total)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'account.invoice',
            'docs': docs,
            'thaibahttext': thaibahttext,
        }
