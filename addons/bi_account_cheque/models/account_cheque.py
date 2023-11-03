# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
import odoo.addons.decimal_precision as dp
from datetime import date, datetime
from odoo.exceptions import UserError
import json
from odoo.tools import float_is_zero, float_compare


class AccountCheque(models.Model):
    _name = "account.cheque"
    _order = 'id desc'

    sequence = fields.Char(string='Sequence', readonly=True ,copy=True, index=True)
    name = fields.Char(string="Name",required="1")
    bank_account_id = fields.Many2one('account.account','Bank Account')
    account_cheque_type = fields.Selection([('incoming','Incoming'),('outgoing','Outgoing')],string="Cheque Type")
    cheque_number = fields.Char(string="Cheque Number",required=True)
    amount = fields.Float(string="Amount",required=True)
    re_amount = fields.Float(string="Remaining Amount",compute='_get_outstanding_info',)
    cheque_date = fields.Date(string="Cheque Date",default=datetime.now().date())
    cheque_given_date = fields.Date(string="Cheque Given Date")
    cheque_receive_date = fields.Date(string="Cheque Receive Date")
    cheque_return_date = fields.Date(string="Cheque Return Date")
    payee_user_id = fields.Many2one('res.partner',string="Payee",required="1")
    credit_account_id = fields.Many2one('account.account',string="Credit Account")
    debit_account_id = fields.Many2one('account.account',sring="Debit Account")
    comment = fields.Text(string="Comment")
    attchment_ids = fields.One2many('ir.attachment','account_cheque_id',string="Attachment")
    status = fields.Selection([('draft','Draft'),('registered','Registered'),('bounced','Bounced'),('return','Returned'),('cashed','Done'),('cancel','Cancel')],string="Status",default="draft",copy=False, index=True, track_visibility='onchange')
    
    status1 = fields.Selection([('draft','Draft'),('registered','Registered'),('bounced','Bounced'),('return','Returned'),('deposited','Deposited'),('transfered','Transfered'),('cashed','Done'),('cancel','Cancel')],string="Status",default="draft",copy=False, index=True, track_visibility='onchange')
    
    journal_id = fields.Many2one('account.journal',string="Journal",required=True)
    company_id = fields.Many2one('res.company',string="Company",required=True)
    journal_items_count =  fields.Integer(compute='_active_journal_items',string="Journal Items") 
    invoice_ids = fields.One2many('account.invoice','account_cheque_id',string="Invoices",compute="_count_account_invoice",)
    
    attachment_count  =  fields.Integer('Attachments', compute='_get_attachment_count')
    in_count = fields.Boolean('Invoice',compute='_get_in_count')
    is_partial = fields.Boolean(string='Not reconciled')
    
    @api.model 
    def default_get(self, flds): 
        result = super(AccountCheque, self).default_get(flds)
        res = self.env['res.config.settings'].sudo().search([], limit=1, order="id desc")
        user_company_id = self.env.user.company_id
        if self._context.get('default_account_cheque_type') == 'incoming':
            result['credit_account_id'] = user_company_id.in_credit_account_id.id
            result['debit_account_id'] = user_company_id.in_debit_account_id.id
            result['journal_id'] = user_company_id.specific_journal_id.id
            result['company_id'] = user_company_id.id
        else:
            result['credit_account_id'] = user_company_id.out_credit_account_id.id
            result['debit_account_id'] = user_company_id.out_debit_account_id.id
            result['journal_id'] = user_company_id.specific_journal_id.id 
            result['company_id'] = user_company_id.id
        return result 
        
    def open_payment_matching_screen(self):
        # Open reconciliation view for customers/suppliers
        move_line_id = False
        account_move_line_ids = self.env['account.move.line'].search([('partner_id','=',self.payee_user_id.id)])
        for move_line in account_move_line_ids:
            if move_line.account_id.reconcile:
                move_line_id = move_line.id
                break;
        action_context = {'company_ids': [self.company_id.id], 'partner_ids': [self.payee_user_id.id]}
        if self.account_cheque_type == 'incoming':
            action_context.update({'mode': 'customers'})
        elif self.account_cheque_type == 'outgoing':
            action_context.update({'mode': 'suppliers'})
        if account_move_line_ids:
            action_context.update({'move_line_id': move_line_id})


        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }
        
    @api.multi
    def _count_account_invoice(self):
        invoice_list = []
        for invoice in self.payee_user_id.invoice_ids:
            if invoice.state != 'paid':
                if self.account_cheque_type == 'incoming':
                    if invoice.type == 'out_invoice':
                        invoice_list.append(invoice.id)
                        self.invoice_ids = [(6, 0, invoice_list)]
                if self.account_cheque_type == 'outgoing':
                    if invoice.type == 'in_invoice':
                        invoice_list.append(invoice.id)
                        self.invoice_ids = [(6, 0, invoice_list)]
        return

    def _get_in_count(self):
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        for move in journal_item_ids:
            for line in move.line_ids:
                reference = self.sequence + '- ' + self.cheque_number + '- ' + 'Registered'
                credit_account = line.search([('ref','=',reference),('account_id','=',self.credit_account_id.id)])
                if credit_account:
                    if credit_account.reconciled == True:
                        if self.account_cheque_type == 'incoming':
                            self.write({'status1':'cashed'})
                        if self.account_cheque_type == 'outgoing':
                            self.write({'status':'cashed'})

        if self.amount != self.re_amount:
           self.write({'is_partial':True}) 
        else:
           self.write({'is_partial':False}) 

        return

    @api.one
    def _get_outstanding_info(self):
        for invoice in self.payee_user_id.invoice_ids:
            domain = [('account_id', '=', invoice.account_id.id),
                      ('partner_id', '=', self.env['res.partner']._find_accounting_partner(invoice.partner_id).id),
                      ('reconciled', '=', False),
                      ('move_id.state', '=', 'posted'),
                      '|',
                        '&', ('amount_residual_currency', '!=', 0.0), ('currency_id','!=', None),
                        '&', ('amount_residual_currency', '=', 0.0), '&', ('currency_id','=', None), ('amount_residual', '!=', 0.0)]
            if invoice.type in ('out_invoice', 'in_refund'):
                domain.extend([('credit', '>', 0), ('debit', '=', 0)])
                type_payment = _('Outstanding credits')
            else:
                domain.extend([('credit', '=', 0), ('debit', '>', 0)])
                type_payment = _('Outstanding debits')
            info = {'title': '', 'outstanding': True, 'content': [], 'invoice_id': invoice.id}
            lines = self.env['account.move.line'].search(domain)
            currency_id = invoice.currency_id
            if len(lines) != 0:
                for line in lines:
                    # get the outstanding residual value in invoice currency
                    if line.currency_id and line.currency_id == invoice.currency_id:
                        amount_to_show = abs(line.amount_residual_currency)
                    else:
                        currency = line.company_id.currency_id
                        amount_to_show = currency._convert(abs(line.amount_residual), invoice.currency_id, invoice.company_id, line.date or fields.Date.today())
                    if float_is_zero(amount_to_show, precision_rounding=invoice.currency_id.rounding):
                        continue
                    if line.ref :
                        title = '%s : %s' % (line.move_id.name, line.ref)
                    else:
                        title = line.move_id.name
                    if self.account_cheque_type == 'incoming':
                        if self.status1 in ('cashed','deposited','return'):
                            amount_to_show = 0.0
                    if self.account_cheque_type == 'outgoing':
                        if self.status in ('cashed','return'):
                            amount_to_show = 0.0
                    self.re_amount = amount_to_show
   

        
    @api.multi
    def _active_journal_items(self):
        list_of_move_line = []
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        for move in journal_item_ids:
            for line in move.line_ids:
                list_of_move_line.append(line.id)
        item_count = len(list_of_move_line)
        journal_items.journal_items_count = item_count
        return
        
    @api.multi
    def action_view_jornal_items(self):
        self.ensure_one()
        list_of_move_line = []
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        for move in journal_item_ids:
            for line in move.line_ids:
                list_of_move_line.append(line.id)
        return {
            'name': 'Journal Items',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'domain': [('id', '=', list_of_move_line)],
        }
        
    @api.multi
    def _get_attachment_count(self):
        for cheque in self:
            attachment_ids = self.env['ir.attachment'].search([('account_cheque_id','=',cheque.id)])
            cheque.attachment_count = len(attachment_ids)
        
    @api.multi
    def attachment_on_account_cheque(self):
        self.ensure_one()
        return {
            'name': 'Attachment.Details',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'ir.attachment',
            'domain': [('account_cheque_id', '=', self.id)],
        }
        
    @api.model
    def create(self, vals):
        journal = self.env['account.journal'].browse(vals['journal_id'])
        sequence = journal.sequence_id
        vals['sequence'] = sequence.with_context(ir_sequence_date=datetime.today().date().strftime("%Y-%m-%d")).next_by_id()
        result = super(AccountCheque, self).create(vals)
        return result
        
    @api.multi
    def set_to_submit(self):
        account_move_obj = self.env['account.move']
        move_lines = []
        if self.account_cheque_type == 'incoming':
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_receive_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Registered',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
            self.status1 = 'registered'
        else:
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_given_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Registered',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'debit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id, 
                    'credit' : self.amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.post()
            self.status = 'registered'
        return account_move

    @api.multi
    def set_to_bounced(self):
        account_move_obj = self.env['account.move']
        move_lines = []
        if self.account_cheque_type == 'incoming':
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_receive_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Bounced',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id, 
                    'debit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.payee_user_id.property_account_receivable_id.id, 
                    'credit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            self.status1 = 'bounced'
        else:
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_given_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Bounced',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.payee_user_id.property_account_payable_id.id, 
                    'debit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'credit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            self.status = 'bounced'
        return account_move      

    @api.multi
    def set_to_return(self):
        account_move_obj = self.env['account.move']
        move_lines = []
        list_of_move_line = [] 
        for journal_items in self:
            journal_item_ids = self.env['account.move'].search([('account_cheque_id','=',journal_items.id)])
        
        matching_dict = []
        for move in journal_item_ids:
            for line in move.line_ids:
                if line.full_reconcile_id:
                    matching_dict.append(line)
                                    
        if len(matching_dict) != 0:
            rec_id = matching_dict[0].full_reconcile_id.id
            a = self.env['account.move.line'].search([('full_reconcile_id','=',rec_id)])
            
            for move_line in a:
                move_line.remove_move_reconcile()
        
        if self.account_cheque_type == 'incoming':
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_receive_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Returned',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id, 
                    'debit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'credit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            self.status1 = 'return'
            self.cheque_return_date = datetime.now().date()
        else:
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_given_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Returned',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.credit_account_id.id, 
                    'debit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.payee_user_id.id,
                    'account_id' : self.debit_account_id.id, 
                    'credit' : self.re_amount ,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : self.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            self.status = 'return'
            self.cheque_return_date = datetime.now().date()
        return account_move           

               

    @api.multi
    def set_to_deposite(self):
        account_move_obj = self.env['account.move']
        move_lines = []
        if self.account_cheque_type == 'incoming':
            vals = {
                    'name' : self.name,
                    'date' : self.cheque_receive_date,
                    'journal_id' : self.journal_id.id,
                    'company_id' : self.company_id.id,
                    'state' : 'draft',
                    'ref' : self.sequence + '- ' + self.cheque_number + '- ' + 'Deposited',
                    'account_cheque_id' : self.id
            }
            account_move = account_move_obj.create(vals)
            res = self.env['res.config.settings'].search([], limit=1, order="id desc")
            if res:
                debit_vals = {
                        'partner_id' : self.payee_user_id.id,
                        'account_id' : self.env.user.company_id.deposite_account_id.id, 
                        'debit' : self.re_amount ,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : self.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_vals = {
                        'partner_id' : self.payee_user_id.id,
                        'account_id' : self.debit_account_id.id, 
                        'credit' : self.re_amount ,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : self.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))
            else:
                debit_vals = {
                        'partner_id' : self.payee_user_id.id,
                        'account_id' : self.credit_account_id.id, 
                        'debit' : self.re_amount ,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : self.company_id.id,
                }
                move_lines.append((0, 0, debit_vals))
                credit_vals = {
                        'partner_id' : self.payee_user_id.id,
                        'account_id' : self.debit_account_id.id, 
                        'credit' : self.re_amount ,
                        'date_maturity' : datetime.now().date(),
                        'move_id' : account_move.id,
                        'company_id' : self.company_id.id,
                }
                move_lines.append((0, 0, credit_vals))                
            account_move.write({'line_ids' : move_lines})
            account_move.action_post()
            self.status1 = 'deposited'
            return account_move          
                
    @api.multi
    def set_to_cancel(self): 
        if self.account_cheque_type == 'incoming':       
            self.status1 = 'cancel' 
        else:
            self.status = 'cancel'

class ChequeWizard(models.TransientModel):
    _name = 'cheque.wizard'

    @api.model 
    def default_get(self, flds): 
        result = super(ChequeWizard, self).default_get(flds)
        account_cheque_id = self.env['account.cheque'].browse(self._context.get('active_id'))
        if account_cheque_id.account_cheque_type == 'outgoing':
            result['is_outgoing'] = True
        return result
        
    @api.multi
    def create_cheque_entry(self):
        account_cheque = self.env['account.cheque'].browse(self._context.get('active_ids'))
        account_move_obj = self.env['account.move']
        move_lines = []
        if account_cheque.account_cheque_type == 'incoming':
            vals = {
                    'name' : account_cheque.name,
                    'date' : self.chequed_date,
                    'journal_id' : account_cheque.journal_id.id,
                    'company_id' : account_cheque.company_id.id,
                    'state' : 'draft',
                    'ref' : account_cheque.sequence + '- ' + account_cheque.cheque_number + '- ' + 'Cashed',
                    'account_cheque_id' : account_cheque.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : account_cheque.debit_account_id.id, 
                    'debit' : account_cheque.re_amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : account_cheque.bank_account_id.id, 
                    'credit' : account_cheque.re_amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_cheque.status1 = 'cashed'

        #Outgoing cheque
        else:
            vals = {
                    'name' : account_cheque.name,
                    'date' : self.chequed_date,
                    'journal_id' : account_cheque.journal_id.id,
                    'company_id' : account_cheque.company_id.id,
                    'state' : 'draft',
                    'ref' : account_cheque.sequence + '- ' + account_cheque.cheque_number + '- ' + 'Cashed',
                    'account_cheque_id' : account_cheque.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : account_cheque.credit_account_id.id, 
                    'debit' : account_cheque.re_amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : account_cheque.payee_user_id.id,
                    'account_id' : self.bank_account_id.id, 
                    'credit' : account_cheque.re_amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_move.action_post()
            account_cheque.status = 'cashed'
        return account_move


    chequed_date = fields.Date(string="Cheque Date")
    bank_account_id = fields.Many2one('account.account',string="Bank Account")
    is_outgoing = fields.Boolean(string="Is Outgoing",default=False)
    
class ChequeTransferedWizard(models.TransientModel):
    _name = 'cheque.transfered.wizard'

    @api.multi
    def create_ckeck_transfer_entry(self):
        account_cheque = self.env['account.cheque'].browse(self._context.get('active_ids'))
        account_move_obj = self.env['account.move']
        move_lines = []
        if account_cheque.account_cheque_type == 'incoming':
            vals = {
                    'name' : account_cheque.name,
                    'date' : self.transfered_date,
                    'journal_id' : account_cheque.journal_id.id,
                    'company_id' : account_cheque.company_id.id,
                    'state' : 'draft',
                    'ref' : account_cheque.sequence + '- ' + account_cheque.cheque_number + '- ' + 'Transfered',
                    'account_cheque_id' : account_cheque.id
            }
            account_move = account_move_obj.create(vals)
            debit_vals = {
                    'partner_id' : self.contact_id.id,
                    'account_id' : account_cheque.credit_account_id.id, 
                    'debit' : account_cheque.re_amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, debit_vals))
            credit_vals = {
                    'partner_id' : self.contact_id.id,
                    'account_id' : account_cheque.debit_account_id.id, 
                    'credit' : account_cheque.re_amount,
                    'date_maturity' : datetime.now().date(),
                    'move_id' : account_move.id,
                    'company_id' : account_cheque.company_id.id,
            }
            move_lines.append((0, 0, credit_vals))
            account_move.write({'line_ids' : move_lines})
            account_cheque.status1 = 'transfered'
            account_cheque.payee_user_id = self.contact_id.id
            return account_move
        
    transfered_date = fields.Date(string="Transfered Date")
    contact_id = fields.Many2one('res.partner',string="Contact")
    
class AccountMoveLine(models.Model):
    _inherit='account.move'

    account_cheque_id  =  fields.Many2one('account.cheque', 'Journal Item')

class AccountInvoice(models.Model):
    _inherit='account.invoice'

    account_cheque_id  =  fields.Many2one('account.cheque', 'Account Cheque')

class ReportWizard(models.TransientModel):
    _name = "report.wizard"

    from_date = fields.Date('From Date', required = True)
    to_date = fields.Date('To Date',required = True)
    cheque_type = fields.Selection([('incoming','Incoming'),('outgoing','Outgoing')],string="Cheque Type",default='incoming')
    
    
    @api.multi
    def submit(self):
        inc_temp = []
        out_temp = []
        temp = [] 
        
        if self.cheque_type == 'incoming':
            in_account_cheque_ids = self.env['account.cheque'].search([(str('cheque_date'),'>=',self.from_date),(str('cheque_date'),'<=',self.to_date),('account_cheque_type','=','incoming')])
        
            if not in_account_cheque_ids:
                raise UserError(_('There Is No Any Cheque Details.'))
            else:
                for inc in in_account_cheque_ids:
                    temp.append(inc.id)
            
        if self.cheque_type == 'outgoing':
            out_account_cheque_ids = self.env['account.cheque'].search([(str('cheque_date'),'>=',self.from_date),(str('cheque_date'),'<=',self.to_date),('account_cheque_type','=','outgoing')])
            
            if not out_account_cheque_ids:
                raise UserError(_('There Is No Any Cheque Details.'))
            else:
                for out in out_account_cheque_ids:
                    temp.append(out.id)
                               
        data = temp
        in_data = inc_temp
        out_data = out_temp
        datas = {
            'ids': self._ids,
            'model': 'account.cheque',
            'form': data,
            'from_date':self.from_date,
            'to_date':self.to_date,
            'cheque_type' : self.cheque_type,
        }
        return self.env.ref('bi_account_cheque.account_cheque_report_id').report_action(self,data=datas)

class IrAttachment(models.Model):
    _inherit='ir.attachment'

    account_cheque_id  =  fields.Many2one('account.cheque', 'Attchments')
    
