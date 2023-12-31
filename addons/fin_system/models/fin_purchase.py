# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, date
from odoo.exceptions import UserError
from lxml import etree
import logging
from odoo.osv import orm
from odoo.addons.fin_system.models.fin_middleware import message_log_stamp
_logger = logging.getLogger(__name__)

DUMMY_EMPLOYEE = 4596
DEV_DUMMY_EMPLOYEE = 4595

POSITION_INDEX = [(1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(9,9),(10,10),
                  (11,11),(12,12),(13,13),(14,14),(15,15),(16,16),(17,17),(18,18),(19,19),(20,20)]

PRIORITY = [('1_normal', 'Normal'),
                   ('0_urgent', 'Urgent')]
                  
POSITION_CLASS = {
    "DirectorOfDepartment" : "fw_pfb_related_director_of_department",
    "DirectorOfEEC" : "fw_pfb_related_directorofeec",
    "DirectorOfStrategy" : "fw_pfb_related_directorofstrategy",
    "BudgetOwner" : "fw_pfb_related_budgetowner",
    "DirectorOfFinance" : "fw_pfb_related_directoroffinance",
    "ManagerOfStock" : "fw_pfb_related_managerofstock",
    "AssistantOfOffice" : "fw_pfb_related_assistantofoffice",
    "AssistantOfOfficeSecretary" : "fw_pfb_related_assistantofoffice",
    "DeputyOfOffice" : "fw_pfb_related_deputyofoffice",
    "DeputyOfOfficeSecretary" : "fw_pfb_related_deputyofoffice",
    "AssistantOfOfficeManagement" : "fw_pfb_related_assistantofofficemanagement",
    "DirectorOfDirector" : "fw_pfb_related_directorofdirector",
    "DirectorOfOfficeSecretary" : "fw_pfb_related_directorofoffice_secretary",
}

STATE_SELECTION = [ ('draft', 'Draft'),
                    ('sent', 'Sent'),
                    ('DirectorOfDepartment', 'Vice President/Director'),
                    ('ManagerOfStock', 'Division Manager of General Affairs and Facilities Division'),
                    ('AssistantOfOffice', 'Executive Vice President'),
                    ('DeputyOfOffice', 'Senior Executive Vice President'),
                    ('SmallNote', 'Small Note'),
                    ('DirectorOfOffice', 'Director'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('reject', 'Reject')]

OLD_FIN_SELECTION = [('project_head_preliminary_supervisor', 'Project head/Preliminary Supervisor'),
                 ('related_department', 'Related Group'),
                 ('deputy_director', 'Deputy Director'),
                 ('director', 'Director')]

APPROVE_POSITION = [('DirectorOfDepartment', 'Vice President/Director'),
                    ('RelatedGroup', 'Related Group'),
                    ('DirectorOfFinance', 'Division Manager of Finance, Accounting and Control Division'),
                    ('ManagerOfStock', 'Division Manager of General Affairs and Facilities Division'),
                    ('AssistantOfOffice', 'Executive Vice President'),
                    ('DeputyOfOffice', 'Senior Executive Vice President'),
                    ('SmallNote', 'Small Note'),
                    ('DirectorOfOffice', 'President/CEO')]


FIN_SELECTION = [('DirectorOfDepartment', 'Vice President Director'),
                    ('DirectorOfEEC', 'Director Of EEC'),
                    ('DirectorOfStrategy', 'Vice President of Strategic Management Department'),
                    ('BudgetOwner', 'Budget Owner'),
                    ('DirectorOfFinance', 'Vice President of Finance and General Affairs Department'),
                    ('ManagerOfStock', 'Division Manager of General Affairs and Facilities Division'),
                    ('AssistantOfOffice', 'Executive Vice President'),
                    ('AssistantOfOfficeSecretary', 'Assistant Team Leader'),
                    ('DeputyOfOffice', 'Senior Executive Vice President'),
                    ('DeputyOfOfficeSecretary', 'Deputy Team Leader'),
                    ('AssistantOfOfficeManagement', 'Group Executive Vice President'),
                    ('DirectorOfDirector', 'Vice President of Agency Administration Department'),
                    ('DirectorOfOffice', 'President/CEO'), 
                    ('DirectorOfOfficeSecretary', 'Senior Team Leader')]

STATE_APPROVE = [('pending', 'Pending'),
                 ('approve', 'Approve'),
                 ('reject', 'Reject')]

FIN_TYPE = [('pors', 'Purchase request of stock')]
FIN_TYPE_PULL_FIN100 = [('proo', 'Purchase reguest of objective')]


class fw_pfb_FS_purchase(models.Model):
    _name = 'fw_pfb_fin_system_purchase'
    _order = 'priority ASC, fin_date DESC, fin_no DESC'

    @api.returns('self')
    def _default_employee_get(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.depends('approver')
    def _get_approver_rights(self):
        rights = ''
        approver_list = []
        for list in self.approver:
            approver_list.append(list.employee_user_id.id)
        if self._uid in approver_list:
            approver = self.env['fw_pfb_fin_system_purchase_approver'].search(
                [('fin_id', '=', self.id), ('employee_user_id.id', '=', self._uid)])
            if len(approver) > 1:
                for ap in approver:
                    rights += ap.fin_position + ' , '
            else:
                rights = approver.fin_position

        else:
            rights = 'fin_user'
        self.approver_rights = rights

    @api.depends('approver')
    def _get_is_director(self):
        rights = ''
        approver_list = []
        for list in self.approver:
            approver_list.append(list.employee_user_id.id)
        if self._uid in approver_list:
            approver = self.env['fw_pfb_fin_system_purchase_approver'].search(
                [('fin_id', '=', self.id), ('employee_user_id.id', '=', self._uid)])
            if len(approver) > 1:
                for ap in approver:
                    rights += ap.fin_position + ' , '
            else:
                rights = approver.fin_position

        else:
            rights = 'fin_user'
        if rights == 'director':
            self.is_director = True

    @api.depends('requester')
    def _check_is_requester(self):
        if self._uid == self.requester.user_id.id:
            self.is_requester = True
        else:
            self.is_requester = False

    @api.depends('can_set_complete')
    def _is_can_set_complete(self):
        self.can_set_complete = False
        usrid = self._uid
        active_model = self._name
        group_id = self.env['res.groups'].search([('name', 'like', 'Can change fin100 to complete')], limit=1)
        if group_id :
            if group_id.users :
                for i in group_id.users :
                    if i.id == usrid and active_model == 'fw_pfb_fin_system_purchase':
                        self.can_set_complete = True

    @api.multi
    def _check_can_cancel(self):
        fin_user = []
        for approver in self.approver:
            fin_user.append(approver.employee_user_id.id)
        fin_user.append(self.requester.user_id.id)
        if self._uid in fin_user:
            self.can_cancel = True
        else:
            self.can_cancel = False

    # @api.depends('is_pr_created')
    # def _get_pr(self):
    #     if self.is_pr_created:
    #         pr_list = []
    #         pr_obj = self.env['fw_ksp_pr'].search([('fin_id', '=', self.id)])
    #         for pr in pr_obj:
    #             pr_list.append(pr.id)
    #         self.pr_ids = pr_list
    #         self.pr_count = len(pr_obj)

    @api.onchange('flow_template')
    def _onchange_flow_template(self):
        self.approver = False
        id =  self.flow_template.id
        
        flow = self.env['fw_pfb_flow_template'].browse( id )
        if flow :
            if flow.approve_line :
                for line in flow.approve_line :
                    data = {
                            "employee_id" : line.emp_name.id,
                            "fin_position" : line.position,
                            "approve_active" : line.data_activate,
                            "approve_position" : line.approve_position,
                            "position_index" : line.position_index
                        }
                    if line.data_activate :
                        data["state"] = "pending"
                    self.approver += self.approver.new( data )
                    
    @api.one
    def _get_please_consider(self):
        self.please_consider = self.fin_type

    # Budget system
    projects_and_plan = fields.Many2one('account.analytic.account')
    budget_department = fields.Many2one('hr.department')
    budget_request = fields.Float()
    has_history = fields.Boolean(string="Has History", default = False)

    # Fin system

    target_approver = fields.Char(string='Target Approver' )

    priority = fields.Selection(PRIORITY, string='Priority', required=True)

    flow_template = fields.Many2one('fw_pfb_flow_template',
                                domain=[('type', '=', 'pors'),('data_activate', '=', True)],
                                string='Flow Template')
                                 
    fin_objective = fields.Many2one('fw_pfb_objective',
                                 string='Objective')
    fin_type = fields.Selection(FIN_TYPE, string='FIN Type', default="pors")

    participantas_quantity = fields.Char(string='Participantas Quantity', default="0")
    place = fields.Many2many("ir.attachment",
                                  "attachment_fin_place_rel",
                                  "attachment_fin_place_id",
                                  "attachment_id",
                                  string="Place")
    operation_date = fields.Many2many("ir.attachment",
                                  "attachment_fin_operation_date_rel",
                                  "attachment_fin_operation_date_id",
                                  "attachment_id",
                                  string="Operation Date")
    seminar_partcipants = fields.Many2many("ir.attachment",
                                  "attachment_fin_seminar_rel",
                                  "attachment_fin_seminar_id",
                                  "attachment_id",
                                  string="Seminar Partcipants")
    other = fields.Text(string='Other')
    estimate_output = fields.Text(string='Estimate')
    please_consider = fields.Selection(FIN_TYPE, string='Please Consider', compute="_get_please_consider")


    fin_no = fields.Char(string='fin NO.',
                         readonly=True, )
    fin_date = fields.Date(string='fin Date',
                           default=lambda self: date.today(),
                           readonly=True)
    requester = fields.Many2one('hr.employee',
                                string='Requester',
                                default=_default_employee_get)
    is_requester = fields.Boolean(string='Is requester',
                                  compute='_check_is_requester')
    is_director = fields.Boolean(string="Is director",
                                 compute='_get_is_director')
    department = fields.Many2one('hr.department',
                                 string='Department',
                                 related='requester.department_id')
    state = fields.Selection(STATE_SELECTION,
                             default='draft',
                             required=True)
    subject = fields.Char(string='Subject')
    subject_to = fields.Char(string='Subject To.')
    objective = fields.Text(string='Objective Extra')
    participants = fields.Many2many('hr.employee')
    template_id = fields.Many2many('sale.order.template',
                                   'so_template_fin_rel',
                                   'so_id',
                                   'fin_id',
                                   readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   domain=[('fin_ok', '=', True)])
    fin_lines = fields.One2many('fw_pfb_fin_system_purchase_line',
                                'fin_id',
                                copy=True, )
    is_fin_lock = fields.Boolean(string="Lock")
    fin_ref = fields.Char(string='Reference')
    fin_remark = fields.Text(string='Remark')
    price_total = fields.Float(string='Request Amount', compute='_compute_total')
    approver = fields.One2many('fw_pfb_fin_system_purchase_approver',
                               'fin_id',
                               copy=True,)
    approver_rights = fields.Char(string='Approver Rights',
                                  compute="_get_approver_rights")
    can_cancel = fields.Boolean(string='Can cancel',
                                compute='_check_can_cancel')
    show_fin = fields.Boolean(string='Show FIN', )
    check_reject = fields.Boolean(string='Check Reject')
    fin_projects = fields.One2many('fw_pfb_fin_system_purchase_projects',
                                   'fin_id',
                                   copy=True,
                                   readonly=True)
    attachment = fields.Many2many("ir.attachment",
                                  "attachment_fin_rel",
                                  "attachment_fin_id",
                                  "attachment_id",
                                  string="Attachment")
    can_create_pr = fields.Boolean(compute='_check_can_be_pr')
    # pr_ids = fields.Many2many("fw_ksp_pr",
    #                           string='Purchase Request',
    #                           compute="_get_pr",
    #                           readonly=True,
    #                           copy=False)
    # pr_count = fields.Integer(string='PR Count',
    #                           compute='_get_pr')
    is_pr_created = fields.Boolean(string='Is PR Create?')

    can_set_complete = fields.Boolean(string='Can set to complete', compute="_is_can_set_complete")

    # To filter approver list
    approver_name_list = fields.Text(
        string='Approver Name',
        compute='_compute_approver_list',
        store=True
    )
    # To filter filter in approver list
    action_date_list = fields.Text(
        string='Action Date Approved',
        compute='_compute_approver_list',
        store=True,
    )

    @api.multi
    @api.depends('approver')
    def _compute_approver_list(self):
        for rec in self:
            approver_list = ''
            action_list = ''
            if rec.approver:
                for ap in rec.approver:
                    if ap.employee_id.name:
                        approver_list += ap.employee_id.name + ' '
                    if ap.action_date:
                        action_list += str(ap.action_date)
                rec.approver_name_list = approver_list
                rec.action_date_list = action_list

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        env_fin = self.env['fw_pfb_fin_system_purchase']
        env_fin_approver = self.env['fw_pfb_fin_system_purchase_approver']
        params = self._context.get('params')

        checkRule = False

        if params :
            if "action" in params :
               if params["action"] == 1168 :
                   checkRule = True
        
        res = super(fw_pfb_FS_purchase, self).fields_view_get(
                view_id=view_id, view_type=view_type, toolbar=toolbar,
                submenu=submenu)

        if checkRule :  
            fin_list = env_fin.search([])
            for fin in fin_list:
                fin_user = []
                fin_obj = env_fin.search([('id', '=', fin.id)])
                # fin_user.append(fin_obj.requester.user_id.id)
                if fin_obj.check_reject != True :
                    fin_obj_approve = env_fin_approver.search([
                        ('fin_id', '=', fin.id),
                        ('approve_active', '=', True)
                    ])

                    for approver in fin_obj_approve :
                        if fin_obj.target_approver == approver.approve_position :
                            if approver.employee_user_id :
                                if approver.state == "pending" or approver.state == False :
                                    fin_user.append( approver.employee_user_id.id )
                        
                        if fin_obj.target_approver == "DirectorOfOffice" :
                            if approver.approve_position == "SmallNote" :
                                if approver.state == False or approver.state == "pending" :
                                    if approver.employee_user_id :
                                        fin_user.append( approver.employee_user_id.id )
                        
                        if approver.approve_position == "DirectorOfOffice" :
                            directorCanSee = False
                            for checker in fin_obj_approve :
                                if checker.approve_active and checker.approve_position != "DirectorOfOffice" :
                                    if checker.approve_position == "DirectorOfFinance" or checker.approve_position == "ManagerOfStock" or checker.approve_position == "AssistantOfOffice" or checker.approve_position == "DeputyOfOffice" or checker.approve_position == "SmallNote" :
                                        if checker.state == "approve" :
                                            directorCanSee = True
                    
                            if directorCanSee :
                                if approver.employee_user_id :
                                    fin_user.append( approver.employee_user_id.id )
                                    
                if self._uid in fin_user:
                    if not fin_obj.show_fin : # if show_fin is False
                        fin_obj.show_fin = True
                else:
                    if fin_obj.show_fin : # if show_fin is True
                        fin_obj.show_fin = False
        return res
        
    @api.multi
    def name_get(self):
        return [(cat.id, cat.fin_no) for cat in self]

    @api.model
    def create(self, vals):
        vals['fin_no'] = self.env['ir.sequence'].next_by_code('seq_fw_pfb_fin_purchase')
        if "approver" in vals :
            for ap in vals["approver"] :
                if len(ap) == 3 :
                    datas = ap[2]
                    if "approve_active" in datas :
                        if datas["approve_active"] == True :
                            if "employee_id" in datas :
                                # Change to DUMMY Flag
                                emp_obj = self.env['hr.employee'].search([
                                    ('id', '=', datas['employee_id']),
                                    ('is_dummy', '=', True),
                                ])
                                if emp_obj:
                                    # if datas["employee_id"] == DUMMY_EMPLOYEE or datas["employee_id"] == DEV_DUMMY_EMPLOYEE :
                                    raise UserError(_("Don't use Dummy employee on approver."))
                        
        #order = {key[0]: i for i, key in enumerate(FIN_SELECTION)}
        #sorted_approver = sorted(vals['approver'], key=lambda kv: order[kv[2]['fin_position']])
        #vals['approver'] = sorted_approver
        return super(fw_pfb_FS_purchase, self).create(vals)

    @api.multi
    def fin_sent_to_supervisor(self):
        targetApprover = 'DirectorOfDepartment'

        list = []

        if self.approver :
            for appr in self.approver :
                if appr.approve_active :
                    if appr.approve_position :
                        astate = appr.approve_position
                        if astate not in list :
                            list.append( astate )

            if "DirectorOfDepartment" in list :
                targetApprover = 'DirectorOfDepartment'
            elif "ManagerOfStock" in list :
                targetApprover = 'ManagerOfStock'
            elif "AssistantOfOffice" in list :
                targetApprover = 'AssistantOfOffice'
            elif "DeputyOfOffice" in list :
                targetApprover = 'DeputyOfOffice'
            elif "SmallNote" in list :
                targetApprover = 'SmallNote'
            elif "DirectorOfOffice" in list :
                targetApprover = 'DirectorOfOffice'

        self.write({
            'state': 'sent',
            'target_approver' : targetApprover
        })
        return True

    @api.multi
    def change_to_complete(self):
        self.write({
            'state': 'completed'
        })
        return True

    @api.multi
    def fin_complete(self):
        self.write({
            'state': 'completed'
        })
        return True

    @api.multi
    def fin_cancel(self):
        self.write({
            'state': 'cancelled'
        })
        return True

    @api.multi
    def fin_set_to_draft(self):
        for approver in self.approver:
            approver.write({
                'memo': '',
                'action_date': None,
                'state': 'pending',
            })
        self.write({
            'state': 'draft',
            'target_approver' : False,
            'check_reject': False,
        })
        return True

    @api.multi
    def fin_lock(self):
        self.write({
            'is_fin_lock': True
        })
        return True

    @api.multi
    def fin_unlock(self):
        self.write({
            'is_fin_lock': False
        })
        return True

    @api.multi
    def button_request_fin100(self):
        # create wizard
        self.write({})
        newid = self.env['fin_purchase_request_wiz'].create({})
        return {
                'name': "FIN100 Requests",
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'fin_purchase_request_wiz',
                'view_id': self.env.ref('fin_system.fin_purchase_request_wiz_form').id,
                'res_id':newid.id,
                'type': 'ir.actions.act_window',
                'target': 'new'
          }

    # @api.multi
    # def action_view_fin(self):
    #     pr_ids = self.mapped('pr_ids')
    #     imd = self.env['ir.model.data']
    #     action = imd.xmlid_to_object('fw_ksp_pr.fw_ksp_pr_action_pr')
    #     list_view_id = imd.xmlid_to_res_id('fw_ksp_pr.fw_ksp_pr_tree')
    #     form_view_id = imd.xmlid_to_res_id('fw_ksp_pr.fw_ksp_pr_form')
    #
    #     result = {
    #         'name': action.name,
    #         'type': action.type,
    #         'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'],
    #                   [False, 'calendar'], [False, 'pivot']],
    #         'target': action.target,
    #         'context': action.context,
    #         'res_model': action.res_model,
    #     }
    #     if len(pr_ids) > 1:
    #         result['domain'] = "[('id','in',%s)]" % pr_ids.ids
    #     elif len(pr_ids) == 1:
    #         result['views'] = [(form_view_id, 'form')]
    #         result['res_id'] = pr_ids.ids[0]
    #     else:
    #         result = {'type': 'ir.actions.act_window_close'}
    #     return result

    # @api.multi
    # def fin_create_purchase_request(self):
    #     vals = {}
    #     proj_n_plan = None
    #     request_lines = {}
    #     i = 0
    #     for line in self.fin_lines:
    #         if line.is_pr_ok:
    #             i += 1
    #             request_lines[i] = {
    #                 'product_id': line.product_id.id,
    #                 'name': line.description,
    #                 'product_qty': line.product_uom_qty,
    #                 'product_uom': line.product_uom.id,
    #                 'price_unit': line.price_unit,
    #             }
    #             if line.projects_and_plan:
    #                 proj_n_plan = line.projects_and_plan.id
    #
    #             vals = {
    #                 'fin_id': self.id,
    #                 'projects_and_plan': proj_n_plan,
    #                 'budget_request': self.price_total,
    #             }
    #             res = self.env['fw_ksp_pr'].create(vals)
    #             self.is_pr_created = True
    #             for line in request_lines:
    #                 request_lines[line]['request_id'] = res.id
    #                 self.env['fw_ksp_pr.line'].create(request_lines[line])
    #     return res

    @api.multi
    @api.depends('fin_lines.price_subtotal')
    def _compute_total(self):
        for fin in self:
            total = 0
            for line in fin.fin_lines:
                total += line.price_subtotal
            fin.price_total = total

    @api.multi
    @api.depends('fin_lines.is_pr_ok')
    def _check_can_be_pr(self):
        for fin in self.fin_lines:
            if fin.is_pr_ok:
                self.can_create_pr = True

    @api.onchange('template_id')
    def _onchange_template(self):
        new_lines = []
        for tp_id in self.template_id:
            quote_template = self.env['sale.order.template.line'].sudo().search([('sale_order_template_id', '=', tp_id.id)])
            for quote_line in quote_template:
                new_lines.append((0, 0, {
                    'product_id': quote_line.product_id.id,
                    'description': quote_line.name,
                    'price_unit': quote_line.price_unit,
                    'product_uom_qty': quote_line.product_uom_qty,
                    'product_uom': quote_line.product_uom_id.id,
                }))
        self.fin_lines = new_lines


class fw_pfb_FS_purchaseLines(models.Model):
    _name = 'fw_pfb_fin_system_purchase_line'

    @api.depends('price_unit', 'product_uom_qty')
    def _compute_subtotal(self):
        for line in self:
            line['price_subtotal'] = line.product_uom_qty * line.price_unit
                     

    @api.onchange('product_id')
    def _set_price(self):
        self.price_unit = self.product_id.product_tmpl_id.standard_price
        self.product_uom = self.product_id.product_tmpl_id.uom_id


    @api.model
    def create(self, vals):
        res = super(fw_pfb_FS_purchaseLines, self).create(vals)
        proj_vals = {}
        if res.projects_and_plan:
            line_proj = self.env['fw_pfb_fin_system_purchase_projects'].search([
                ('fin_id', '=', res.fin_id.id),
                ('projects_and_plan.id', '=', res.projects_and_plan.id)
            ])
            if line_proj:
                line_proj.projects_reserve += res.price_subtotal
            else:
                vals = {
                    'fin_id': res.fin_id.id,
                    'projects_and_plan': res.projects_and_plan.id,
                    'projects_reserve': res.price_subtotal,
                }
                projects = self.env['fw_pfb_fin_system_purchase_projects'].create(vals)
        return res

    fin_id = fields.Many2one('fw_pfb_fin_system_purchase',
                             required=True,
                             ondelete='cascade',
                             index=True,
                             copy=False)

    fin_line_id = fields.Char(string='Fin line id')
    fin_type = fields.Selection(FIN_TYPE_PULL_FIN100, string='FIN Type')
    fin100_id = fields.Many2one('fw_pfb_fin_system_100',string=_("Fin100 number"))

    product_id = fields.Many2one('product.product',
                                 domain=[('fin_ok', '=', True)],
                                 required=True)
    is_pr_ok = fields.Boolean(related='product_id.pr_ok')
    description = fields.Char(string='description', )
    product_uom_qty = fields.Float(string='Quantity',
                                   # digits=dp.get_precision('Product Unit of Measure'),
                                   required=True,
                                   default=1.0)
    product_uom = fields.Many2one('uom.uom',
                                  string='Unit of Measure',
                                  store=True,
                                  # related='product_id.product_tmpl_id.uom_id',
                                  required=True)
    price_unit = fields.Float('Unit Price',
                              required=True,
                              # digits=dp.get_precision('Product Price'),
                              store=True,
                              # default=_default_price,
                              # default='product_id.lst_price',
                              )
    price_subtotal = fields.Float(compute='_compute_subtotal',
                                  string='Subtotal',
                                  readonly=True,
                                  store=True, )
    projects_and_plan = fields.Many2one('account.analytic.account')



class fw_pfb_FS_purchaseApprover(models.Model):
    _name = 'fw_pfb_fin_system_purchase_approver'        
    _order = 'position_index asc'

    @api.model
    def _show_fin(self):
        for fin in self:
            fin_user = []

            if fin.state != 'approve' :
                if fin.fin_id.target_approver == fin.approve_position :
                    fin_user.append(fin.employee_user_id.id)
                
                if fin.approve_position == "SmallNote" :
                    if fin.fin_id.target_approver == "DirectorOfOffice" :
                        fin_user.append(fin.employee_user_id.id)
                
                
                if fin.approve_position == "DirectorOfOffice" :
                    if fin.approve_active == True  :
                        canApproveFin = False
                        for checker in fin.fin_id.approver :
                            if checker.approve_active and checker.approve_position != "DirectorOfOffice" :
                                if checker.approve_position == "DirectorOfFinance" or checker.approve_position == "ManagerOfStock" or checker.approve_position == "AssistantOfOffice" or checker.approve_position == "DeputyOfOffice" or checker.approve_position == "SmallNote" :
                                    if checker.state == "approve" :
                                        canApproveFin = True
                        if canApproveFin :
                            fin_user.append(fin.employee_user_id.id)

            if self._uid in fin_user:
                fin.show_fin = True
            else:
                fin.show_fin = False

    @api.depends('fin_position')
    def _is_related_department(self):
        for fin in self:
            if fin.fin_position == 'RelatedGroup':
                fin.is_related_department = True
            else:
                fin.is_related_department = False

    @api.depends('fin_position')
    def _is_not_related_department(self):
        for fin in self:
            if fin.fin_position != 'RelatedGroup':
                fin.is_not_related_department = True
            else:
                fin.is_not_related_department = False

    @api.onchange('employee_line')
    def _onchange_employee_line(self):
        if self.employee_line :
            for i in self.employee_line :
                if i.data_activate :
                    self.employee_id = i.name.id

    @api.onchange('approve_active')
    def _onchange_approve_active(self):
        if self.approve_active :
            self.state = "pending"
        else :
            self.state = False


    @api.onchange('need_to_change_employee')
    def _onchange_need_to_change_employee(self):
        if self.need_to_change_employee :
            if self.fin_position :
                if self.fin_position != "DirectorOfOffice" :
                    if self.fin_position in POSITION_CLASS :
                        list = self.env[ POSITION_CLASS[self.fin_position] ].search([])
                        if list :
                            for i in list :
                                eid = False
                                if self.fin_position != "AssistantOfOfficeSecretary" and self.fin_position != "DeputyOfOfficeSecretary" and  self.fin_position != "DirectorOfOffice" :
                                    eid = i.name.id
                                else :
                                    eid = i.secretary.id
                                
                                self.employee_line += self.employee_line.create( { "name" : eid} )
                else :
                    sid = False
                    hasSettings = self.env['fw_pfb_fin_settings2'].search([], limit=1)
                    if hasSettings :
                        for i in hasSettings :
                            fin = self.env['fw_pfb_fin_settings2'].browse( i.id )
                            if fin :
                                if fin.directorOfOffice :
                                    sid = fin.directorOfOffice.id
                                    self.employee_line += self.employee_line.create( {"name" : sid, "data_activate":True} )
        else :
            self.employee_line = False
            
        

    approve_active = fields.Boolean(string='Active')
    position_index = fields.Selection(POSITION_INDEX, string='Approve Position')

    fin_id = fields.Many2one('fw_pfb_fin_system_purchase',
                             required=True,
                             ondelete='cascade',
                             index=True)
    employee_id = fields.Many2one('hr.employee',
                                  required=True,
                                  domain=[('user_id', '!=', None),
                                          ('fin_can_approve', '=', True)])
    fin_position = fields.Selection(FIN_SELECTION, string='FIN Position')
    approve_position = fields.Selection(APPROVE_POSITION, string='Approve Position', required=True)
    employee_user_id = fields.Many2one('res.users',
                                       related='employee_id.user_id',
                                       readonly=True, )
    action_date = fields.Datetime(string='Action Date')
    state = fields.Selection(STATE_APPROVE,
                             string='State approve',
                             default='pending')
    memo = fields.Text(string='Memo')
    show_fin = fields.Boolean(string='Show FIN',
                              compute=_show_fin)
    is_related_department = fields.Boolean(string='Show FIN',
                                           compute=_is_related_department)
    is_not_related_department = fields.Boolean(string='Show FIN',
                                               compute=_is_not_related_department)

    employee_line = fields.One2many('fw_pfb_approve_employee_list_purchase', 'release_id', string='Please select employee')

    need_to_change_employee = fields.Boolean(string='Need to change employee', default=False)


    @api.model
    def create(self, vals):
        vals["need_to_change_employee"] = False
        vals["employee_line"] = False
        return super(fw_pfb_FS_purchaseApprover, self).create(vals)

    @api.multi
    def write(self, vals):
        vals["need_to_change_employee"] = False
        vals["employee_line"] = False
        return super(fw_pfb_FS_purchaseApprover, self).write(vals)


class fw_pfb_FS_purchaseBudget(models.Model):
    _name = 'fw_pfb_fin_system_purchase_projects'

    @api.depends('projects_reserve', 'projects_residual')
    def _compute_residual(self):
        for line in self:
            line['projects_residual_amount'] = line.projects_residual - line.projects_reserve

    fin_id = fields.Many2one('fw_pfb_fin_system_purchase',
                             required=True,
                             ondelete='cascade',
                             index=True,
                             copy=False)
    projects_and_plan = fields.Many2one('account.analytic.account',
                                        readonly=True,)
    projects_residual = fields.Float(string='Residual',
                                     related='projects_and_plan.budget_balance',
                                     readonly=True)
    projects_reserve = fields.Float(string='Reserve',
                                    readonly=True)
    projects_residual_amount = fields.Float(string='Residual amount',
                                            compute='_compute_residual',
                                            readonly=True)

class fw_pfb_FS_purchaseApproveWizard(models.TransientModel):
    _name = 'wizard.fw_pfb_fin_system_purchase_approver'

    memo = fields.Text('Memo',
                       required=True)

    @api.multi
    def acknowledge_fin_purchase(self):
        context = self._context
        if context:
            approver_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([('id', '=', context['active_id'])])
            if approver_obj.state != 'DirectorOfOffice' : 
                if approver_obj.approve_position == 'DirectorOfDepartment':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'
                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                        ('approve_active', '=', True),
                        ('approve_position', '=', 'DirectorOfDepartment')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'DirectorOfDepartment')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'DirectorOfDepartment'
                            approver_obj.fin_id.target_approver = 'ManagerOfStock'

                elif approver_obj.approve_position == 'ManagerOfStock' :
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'ManagerOfStock')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'ManagerOfStock')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'ManagerOfStock'
                            approver_obj.fin_id.target_approver = 'AssistantOfOffice'

                
                elif approver_obj.approve_position == 'AssistantOfOffice':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'AssistantOfOffice')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'AssistantOfOffice')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'AssistantOfOffice'
                            approver_obj.fin_id.target_approver = 'DeputyOfOffice'
                    

                elif approver_obj.approve_position == 'DeputyOfOffice':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'DeputyOfOffice')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'DeputyOfOffice')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'DeputyOfOffice'
                            approver_obj.fin_id.target_approver = 'SmallNote'
                    
                elif approver_obj.approve_position == 'SmallNote':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'SmallNote'),
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj= self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'SmallNote'),
                        ])

                        if len(check_related_obj) > 0 and approver_obj.fin_id.state != 'SmallNote' :
                            approver_obj.fin_id.state = 'SmallNote'
                            approver_obj.fin_id.target_approver = 'DirectorOfOffice'

                elif approver_obj.approve_position == 'DirectorOfOffice':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'
                    approver_obj.fin_id.state = 'DirectorOfOffice'
                    approver_obj.fin_id.target_approver = "DirectorOfOffice"
                else:
                    raise UserError(_('You can not do Approve'))

                if approver_obj.fin_id.target_approver != 'DirectorOfOffice' :
                    list = []
                    targetApprover = approver_obj.fin_id.target_approver
                    for appr in approver_obj.fin_id.approver :
                        if appr.approve_active :
                            if appr.approve_position :
                                astate = appr.approve_position
                                if astate not in list :
                                    list.append( astate )

                    if targetApprover not in list :
                        if targetApprover == "ManagerOfStock" :
                            approver_obj.fin_id.target_approver = "AssistantOfOffice"
                            targetApprover = "AssistantOfOffice"
                                        
                        if targetApprover not in list :
                            if targetApprover == "AssistantOfOffice" :
                                approver_obj.fin_id.target_approver = "DeputyOfOffice"
                                targetApprover = "DeputyOfOffice"
                        
                        if targetApprover not in list :
                            if targetApprover == "DeputyOfOffice" :
                                approver_obj.fin_id.target_approver = "SmallNote"
                                targetApprover = "SmallNote"
                        
                        if targetApprover not in list :
                            if targetApprover == "SmallNote" :
                                approver_obj.fin_id.target_approver = "DirectorOfOffice"
                                targetApprover = "DirectorOfOffice"
            
        res = {'type': 'ir.actions.client', 'tag': 'reload'}
        return res

    @api.multi
    def approve_fin_purchase(self):
        context = self._context
        if context:
            approver_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([('id', '=', context['active_id'])])
            if approver_obj.state != 'DirectorOfOffice' : 
                if approver_obj.approve_position == 'DirectorOfDepartment':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'
                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                        ('approve_active', '=', True),
                        ('approve_position', '=', 'DirectorOfDepartment')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'DirectorOfDepartment')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'DirectorOfDepartment'
                            approver_obj.fin_id.target_approver = 'ManagerOfStock'

                elif approver_obj.approve_position == 'ManagerOfStock' :
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'ManagerOfStock')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'ManagerOfStock')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'ManagerOfStock'
                            approver_obj.fin_id.target_approver = 'AssistantOfOffice'

                elif approver_obj.approve_position == 'AssistantOfOffice':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'AssistantOfOffice')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'AssistantOfOffice')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'AssistantOfOffice'
                            approver_obj.fin_id.target_approver = 'DeputyOfOffice'
                    

                elif approver_obj.approve_position == 'DeputyOfOffice':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'DeputyOfOffice')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'DeputyOfOffice')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'DeputyOfOffice'
                            approver_obj.fin_id.target_approver = 'SmallNote'
                    
                elif approver_obj.approve_position == 'SmallNote':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'SmallNote'),
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj= self.env['fw_pfb_fin_system_purchase_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'SmallNote'),
                        ])

                        if len(check_related_obj) > 0 and approver_obj.fin_id.state != 'SmallNote' :
                            approver_obj.fin_id.state = 'SmallNote'
                            approver_obj.fin_id.target_approver = 'DirectorOfOffice'

                elif approver_obj.approve_position == 'DirectorOfOffice':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'
                    approver_obj.fin_id.state = 'DirectorOfOffice'
                    approver_obj.fin_id.target_approver = "DirectorOfOffice"
                else:
                    raise UserError(_('You can not do Approve'))

                if approver_obj.fin_id.target_approver != 'DirectorOfOffice' :
                    list = []
                    targetApprover = approver_obj.fin_id.target_approver
                    for appr in approver_obj.fin_id.approver :
                        if appr.approve_active :
                            if appr.approve_position :
                                astate = appr.approve_position
                                if astate not in list :
                                    list.append( astate )
                    if targetApprover not in list :
                        if targetApprover == "ManagerOfStock" :
                            approver_obj.fin_id.target_approver = "AssistantOfOffice"
                            targetApprover = "AssistantOfOffice"
                                        
                        if targetApprover not in list :
                            if targetApprover == "AssistantOfOffice" :
                                approver_obj.fin_id.target_approver = "DeputyOfOffice"
                                targetApprover = "DeputyOfOffice"
                        
                        if targetApprover not in list :
                            if targetApprover == "DeputyOfOffice" :
                                approver_obj.fin_id.target_approver = "SmallNote"
                                targetApprover = "SmallNote"
                        
                        if targetApprover not in list :
                            if targetApprover == "SmallNote" :
                                approver_obj.fin_id.target_approver = "DirectorOfOffice"
                                targetApprover = "DirectorOfOffice"
            
        res = {'type': 'ir.actions.client', 'tag': 'reload'}
        return res

    @api.multi
    def reject_fin_purchase(self):
        context = self._context
        if context:
            approver_obj = self.env['fw_pfb_fin_system_purchase_approver'].search([('id', '=', context['active_id'])])
            approver_obj.memo = self.memo
            approver_obj.action_date = datetime.now()
            approver_obj.state = 'reject'
            approver_obj.fin_id.check_reject = True
            approver_obj.fin_id.has_history = True
            approver_obj.fin_id.state = "reject"
            #raise UserError(_('You can not do Reject'))

        res = {'type': 'ir.actions.client', 'tag': 'reload'}
        return res

class fw_pfb_approve_employee_list_purchase(models.TransientModel):
    _name = 'fw_pfb_approve_employee_list_purchase'

    release_id = fields.Many2one('fw_pfb_fin_system_purchase_approver')

    data_activate = fields.Boolean(string='Active')
    name = fields.Many2one('hr.employee', string='Employee Name')



class pfb_FS100CreatePRWizard(models.TransientModel):
    _name = 'wizard.fin.system.100.create.pr'

    fin_100_id = fields.Many2one(
            'fw_pfb_fin_system_100',
            required=True
    )
    pr_ids = fields.Many2many(
            'wizard.fin.system.100.create.pr.line',
            'fin_100_pr_rel',
            'wiz_id',
            'line_id',
    )
    
    @api.one
    def create_pr(self):
        fin100_obj = self.env['fw_pfb_fin_system_100'].search([
            ('id', '=', self.fin_100_id.id),
        ])
        vals = {}
        proj_n_plan = None
        request_lines = {}
        i = 0
        date_approve = False
        for line_approve in fin100_obj.approver:
            if line_approve.action_date:
                date_approve = line_approve.action_date
        for line in self.pr_ids:
            if line:
                i += 1
                if line.projects_and_plan:
                    proj_n_plan = line.projects_and_plan.id

                request_lines[i] = {
                    'product_id': line.product_id.id,
                    'name': line.description,
                    'product_qty': line.product_uom_qty,
                    'product_uom_id': line.product_uom.id,
                    'analytic_account_id': proj_n_plan,
                    'estimated_cost': line.price_unit,
                }

                vals = {
                    'fin_id': fin100_obj.id,
                    'origin': fin100_obj.fin_no,
                    'fin_number': fin100_obj.id,
                    'date_approve': date_approve,
                    'requested_by': fin100_obj.requester.user_id.id,
                    'department_id': fin100_obj.department.id,
                    'description': fin100_obj.objective,
                    'analytic_account_id': proj_n_plan,
                }
  
                attachment_res_model = 'purchase.request'
                # Declare to prevent Unbound 
                attribute_pr_id = {}
                middle_price_id = {}
                attachment_participants_id = {}
                attachment_memo_id = {}
                vals['pr_ck'] = False
                vals['pr2_ck'] = False
                vals['pr3_ck'] = False
                vals['pr4_ck'] = False

                # Prepare attachment data
                if fin100_obj.attachment_base_price:
                    vals['pr_ck'] = True
                    attribute_pr_id = {}
                    for key, attachment in enumerate(fin100_obj.attachment_base_price):
                        attribute_pr_id[key] = fin100_obj.env['ir.attachment'].create({
                            'name': attachment.name,
                            'datas': attachment.datas,
                            'datas_fname': attachment.datas_fname,
                            'res_model': attachment_res_model,
                            'res_id': 0,
                        }).id
                if fin100_obj.attachment_work_scope:
                    vals['pr2_ck'] = True
                    middle_price_id = {}
                    for key, attachment in enumerate(fin100_obj.attachment_work_scope):
                        middle_price_id[key] = fin100_obj.env['ir.attachment'].create({
                            'name': attachment.name,
                            'datas': attachment.datas,
                            'datas_fname': attachment.datas_fname,
                            'res_model': attachment_res_model,
                            'res_id': 0,
                        }).id
                if fin100_obj.attachment_participants:
                    vals['pr3_ck'] = True
                    attachment_participants_id = {}
                    for key, attachment in enumerate(fin100_obj.attachment_participants):
                        attachment_participants_id[key] = fin100_obj.env['ir.attachment'].create({
                            'name': attachment.name,
                            'datas': attachment.datas,
                            'datas_fname': attachment.datas_fname,
                            'res_model': attachment_res_model,
                            'res_id': 0,
                        }).id
                if fin100_obj.attachment_memo:
                    vals['pr4_ck'] = True
                    attachment_memo_id = {}
                    for key, attachment in enumerate(fin100_obj.attachment_memo):
                        attachment_memo_id[key] = fin100_obj.env['ir.attachment'].create({
                            'name': attachment.name,
                            'datas': attachment.datas,
                            'datas_fname': attachment.datas_fname,
                            'res_model': attachment_res_model,
                            'res_id': 0,
                        }).id
                ###
                   
                # pr_obj = self.env['purchase.request'].search([
                #     ('fin_id', '=', fin100_obj.id),
                # ], limit=1, order="id DESC")
                # if pr_obj:
                #     # pr_obj.write(vals)
                #     # pr_obj.line_ids.unlink()
                #     # for line in request_lines:
                #     #     request_lines[line]['request_id'] = pr_obj.id
                #     #     pr_obj.line_ids.create(request_lines[line])
                #     # res = pr_obj
                #     res = self.env['purchase.request'].write(vals)
                #     res.line_ids.unlink()
                #     for line in request_lines:
                #         request_lines[line]['request_id'] = res.id
                #         res.line_ids.create(request_lines[line])
                # else:
        res = self.env['purchase.request'].create(vals)
        res.number_pr = res.name
        # INSERT attachment to attribute_pr field
        if vals.get('pr_ck'):
            for api in attribute_pr_id:
                self.env.cr.execute(
                    """INSERT INTO attachment_attribute_pr_rel(attachment_attribute_pr_id, attachment_id)
                    VALUES(%d, %d);""" %
                    (res.id, attribute_pr_id[api])
                )
        # INSERT attachment to mddle_price field
        if vals.get('pr2_ck'):
            for mpi in middle_price_id:
                self.env.cr.execute(
                    """INSERT INTO attachment_middle_price_rel(attachment_middle_price_id, attachment_id)
                    VALUES(%d, %d);""" %
                    (res.id, middle_price_id[mpi])
                )
        # INSERT attachment to attribute_pr2 field
        if vals.get('pr3_ck'):
            for api in attachment_participants_id:
                self.env.cr.execute(
                    """INSERT INTO attachment_attribute_pr2_rel(attachment_attribute_pr2_id, attachment_id)
                    VALUES(%d, %d);""" %
                    (res.id, attachment_participants_id[api])
                )
        # INSERT attachment to attribute_pr3 field
        if vals.get('pr4_ck'):
            for ami in attachment_memo_id:
                self.env.cr.execute(
                    """INSERT INTO attachment_attribute_pr3_rel(attachment_attribute_pr3_id, attachment_id)
                    VALUES(%d, %d);""" %
                    (res.id, attachment_memo_id[ami])
                )
       
        fin100_obj.is_pr_created = True
        for line in request_lines:
            request_lines[line]['request_id'] = res.id
            res.line_ids.create(request_lines[line])
           
        res.attribute_pr.write({
            'res_model': 'purchase.request',
            'res_id': res.id,
        })

        # res = self.env['purchase.request'].create(vals)
        # for line in request_lines:
        #     request_lines[line]['request_id'] = res.id
        #     res.line_ids.create(request_lines[line])
        #
        #     fin100_obj.is_pr_created = True
        log_message = message_log_stamp(res, "Create PR from FIN100", res.write_date)
        res.message_post(body=_(log_message))
                       
        return {
            'name': "Purchase Request",
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.request',
            'res_id': res.id,
            'type': 'ir.actions.act_window',
        }


    @api.model
    def default_get(self, fields):
        res = super(pfb_FS100CreatePRWizard, self).default_get(fields)
        if self._context['active_model'] == 'fw_pfb_fin_system_100':
            fin_100_id = self._context['fin_100_id']
            fin_100_line_obj = self.env['fw_pfb_fin_system_100_line'].search([
                    ('fin_id', '=', fin_100_id),
                ])
            pr_ids = []
            # Get purchase_request to calculate price
            purchase_request_obj = self.env['purchase.request'].search([
                ('fin_id', '=', fin_100_id),
            ])
            # Calculate residual from purchase_request_line
            product_list = {}
            if purchase_request_obj:
                for pr in purchase_request_obj:
                    purchase_request_line_obj = self.env['purchase.request.line'].search([
                        ('request_id', '=', pr.id),
                    ])
                    for pr_line in purchase_request_line_obj:
                        if pr_line.analytic_account_id:
                            if pr_line.analytic_account_id.id not in product_list:
                                product_list[pr_line.analytic_account_id.id] = {
                                            'product_list': []
                                        }
                            if pr_line.product_id.id not in product_list[pr_line.analytic_account_id.id]['product_list']:
                                product_list[pr_line.analytic_account_id.id]['product_list'].append(pr_line.product_id.id)

            for fin_line in fin_100_line_obj:
                if fin_line.projects_and_plan:
                    product_list_compare = product_list[fin_line.projects_and_plan.id]['product_list'] if product_list.get(fin_line.projects_and_plan.id) else []
                    if fin_line.product_id.id not in product_list_compare: 
                        pr_ids.append((0, 0, {
                                'fin100_id': fin_100_id,
                                'fin_line_id': fin_line.id,
                                'product_id': fin_line.product_id.id,
                                'product_id_dummy': fin_line.product_id.id,
                                'description': fin_line.description,
                                'projects_and_plan': fin_line.projects_and_plan.id,
                                'price_unit': fin_line.price_unit,
                                'product_uom_qty': fin_line.product_uom_qty,
                                'product_uom': fin_line.product_uom.id,
                                'description_display': fin_line.description,
                                'projects_and_plan_display': fin_line.projects_and_plan.id,
                                'price_unit_display': fin_line.price_unit,
                                'product_uom_qty_display': fin_line.product_uom_qty,
                                'price_unit_display': fin_line.price_unit,
                                'product_uom_display': fin_line.product_uom.id,
                                'price_unit_limit': fin_line.price_unit,
                                'product_uom_qty_limit': fin_line.product_uom_qty,
                                'price_subtotal_limit': fin_line.price_subtotal
                            }))
            res.update({
                'fin_100_id': fin_100_id,
                'pr_ids': pr_ids,
                })
                # pr_ids = (0, 0, {
                #     'fin100_id': fin_100_id,
                #     'fin_line_id': fin_line.id,
                #     'product_id': fin_line.product_id.id,
                #     'description': fin_line.description,
                #     'projects_and_plan': fin_line.projects_and_plan.id,
                #     'price_unit': fin_line.price_unit,
                #     'product_uom_qty': fin_line.product_uom_qty,
                #     'product_uom': fin_line.product_uom,
                #     })
        return res


class fw_pfb_FS_purchaseLines(models.Model):
    _name = 'wizard.fin.system.100.create.pr.line'

    # wiz_id = fields.Many2one('wizard.fin.system.100.create.pr',
    #                          required=True,
    #                          ondelete='cascade',
    #                          index=True,
    #                          copy=False)

    fin100_id = fields.Many2one(
                    'fw_pfb_fin_system_100',
                    string=_("Fin100 number"),
                    store=True
                )
    product_id = fields.Many2one(
            'product.product',
            required=True,
            store=True
    )
    # Use to tricky for saving data from readonly field 
    product_id_dummy = fields.Many2one(
            'product.product',
            string="Product",
    )
    is_pr_ok = fields.Boolean(related='product_id.pr_ok')
    description = fields.Char(
            string='description',
    )
    description_display = fields.Char(
            string='description',
    )
    product_uom_qty = fields.Float(string='Quantity',
                                   # digits=dp.get_precision('Product Unit of Measure'),
                                   default=1.0)
    product_uom_qty_display = fields.Float(string='Quantity',
                                   # digits=dp.get_precision('Product Unit of Measure'),
                                   default=1.0)
    product_uom = fields.Many2one('uom.uom',
                                  string='Unit of Measure',
                                  )
    product_uom_display = fields.Many2one('uom.uom',
                                  string='Unit of Measure',
                                  )
    price_unit = fields.Float(
            'Unit Price',
            required=True,
    )
    price_unit_display = fields.Float(
            'Unit Price',
    )
    price_subtotal = fields.Float(
            compute='_compute_subtotal',
            string='Subtotal',
    )
    projects_and_plan = fields.Many2one(
        'account.analytic.account',
    )
    projects_and_plan_display = fields.Many2one(
        'account.analytic.account',
    )


    # For validate data not above on this
    price_unit_limit = fields.Float()
    product_uom_qty_limit = fields.Float()
    price_subtotal_limit = fields.Float()

    @api.depends('product_uom_qty', 'price_unit')
    def _compute_subtotal(self):
        for rec in self:
            rec.price_subtotal = rec.product_uom_qty * rec.price_unit
            if rec.price_subtotal > rec.price_subtotal_limit:
                raise UserError('Subtotal can not greater than ' + str(rec.price_subtotal_limit))

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        for rec in self:
            if rec.product_uom_qty > rec.product_uom_qty_limit :
                raise UserError('Product quantity can not greater than ' + str(rec.product_uom_qty_limit))

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        for rec in self:
            if rec.price_unit > rec.price_unit_limit:
                raise UserError('Price unit can not greater than ' + str(rec.price_unit_limit))
