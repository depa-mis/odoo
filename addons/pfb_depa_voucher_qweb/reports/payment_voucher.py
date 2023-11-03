from odoo import api, models, fields, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class BioneVoucherQweb(models.Model):
    _name = "bione.voucher.qweb"

    move_id = fields.Many2one('account.move', )
    journal_id = fields.Char(string='Journal')
    name = fields.Char()
    sh_cost_center_id = fields.Char(string="Cost Center")
    task_id = fields.Char(string='Job Number')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')


class PaymentVoucherForm(models.AbstractModel):
    _name = 'report.pfb_depa_voucher_qweb.payment_voucher_pdf'

    def _convert_date_to_bhuddhist(self, convert_date):
        date_converted = convert_date + relativedelta(years=543)
        date_converted = date_converted.strftime('%d/%m/%Y %H:%M:%S')
        return date_converted

    def _convert_date_to_bhuddhist2(self, convert_date):
        date_converted = convert_date + relativedelta(years=543)
        date_converted = date_converted.strftime('%d/%m/%Y')
        return date_converted

    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        i = 0
        ii = 1
        len_doc = len(docs)
        doc_data = {}
        for doc in docs:
            doc_data[i] = {}
            doc_data[i]['date'] = self._convert_date_to_bhuddhist2(doc.date)
            doc_data[i]['current_date'] = self._convert_date_to_bhuddhist(datetime.now() + timedelta(hours=7))
            doc_data[i]['name'] = doc.name
            doc_data[i]['narration'] = doc.narration
            doc_data[i]['ref'] = doc.ref
            doc_data[i]['sum_credit'] = 0
            doc_data[i]['sum_debit'] = 0
            doc_data[i]['line_ids'] = {}
            doc_data[i]['group_inv'] = []
            doc_data[i]['group_cheque'] = []
            doc_data[i]['partner_sale'] = ''
            doc_data[i]['group_wt'] = []

            line_ids_obj = self.env['account.move.line'].search([
                ('move_id', '=', doc.id)
            ], order='debit desc')
            doc_data[i]['analytic_account'] = ''
            for line in line_ids_obj:
                if line.partner_id.name:
                    doc_data[i]['partner_sale'] = line.partner_id.name
                doc_data[i]['sum_debit'] += line.debit
                doc_data[i]['sum_credit'] += line.credit

            line_payment_obj = self.env['bione.supplier.payment'].search([
                ('move_id', '=', doc.id)
            ])
            line_payment_re_obj = self.env['bione.supplier.receipts'].search([
                ('move_id', '=', doc.id)
            ])
            if line_payment_obj:
                for inv in line_payment_obj.line_ids:
                    for inv_ids in inv[0].name.invoice_line_ids:
                        doc_data[i]['group_inv'].append(inv_ids)

                for wt in line_payment_obj.wht_ids:
                    for wht_lid in wt.line_ids:
                        doc_data[i]['group_wt'].append(wht_lid)

                for cheque in line_payment_obj.cheque_ids:
                    doc_data[i]['group_cheque'].append(cheque)

            if line_payment_re_obj:

                for wt in line_payment_re_obj.wht_ids:
                    for wht_lid in wt.line_ids:
                        doc_data[i]['group_wt'].append(wht_lid)

                for cheque in line_payment_re_obj.cheque_ids:
                    doc_data[i]['group_cheque'].append(cheque)

            doc_data[i]['header'] = 'สำนักงานส่งเสริมเศรษฐกิจดิจิทัล'
            doc_data[i]['header2'] = 'ใบสำคัญจ่าย'
            doc_data[i]['page'] = ii
            i += 1
            ii += 1
        self.env["bione.voucher.qweb"].search([('move_id', '=', docs.id)]).unlink()
        cr = self.env.cr
        sql = ('''SELECT aa.code as account_id, aa.name,
        CASE
        WHEN ml.debit = 0 THEN 'debit'
        WHEN ml.credit = 0 THEN 'credit'
        END as credit_type,
        sum(debit) as debit,sum(credit) as credit FROM "account_move_line" ml
                JOIN account_account aa on aa.id =ml.account_id
                WHERE move_id = %s
                GROUP BY aa.code,aa.name,credit_type''')
        cr.execute(sql, (docs.id,))
        result = cr.dictfetchall()
        for i in result:
            res = {
                "move_id": docs.id,
                "journal_id": i['account_id'] or '',
                "name": i['name'] or '',
                "debit": i['debit'] or 0,
                "credit": i['credit'] or 0,
            }
            self.env["bione.voucher.qweb"].create(res)
        qwe_journal = self.env["bione.voucher.qweb"].search([('move_id', '=', docs.id)], order='debit desc')

        user_crate = self.env['hr.employee'].search([('user_id', '=', doc.create_uid.id)])

        return {
            'doc_ids': docs.ids,
            'doc_model': 'account.move',
            'docs': doc_data,
            'len_doc': len_doc,
            'user_crate': user_crate,
            'qwe_journal': qwe_journal,
        }
