# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError
from lxml import etree
import logging
from odoo.osv import orm
from . import fin_middleware
_logger = logging.getLogger(__name__)

DUMMY_EMPLOYEE = 4596
DEV_DUMMY_EMPLOYEE = 4595

POSITION_INDEX = [(1,1),(2,2),(3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(9,9),(10,10),
                  (11,11),(12,12),(13,13),(14,14),(15,15),(16,16),(17,17),(18,18),(19,19),(20,20)]

PRIORITY = [('1_normal', 'Normal'),
                   ('0_urgent', 'Urgent')]
                  
FIN_TYPE = [('parr', 'Payment and refund request')]

FIN_TYPE_ON_FIN100 = [('eroe', 'Expense request of express'),
                   ('erob', 'Expense request of budget'),
                   ('proo', 'Purchase reguest of objective'),
                   ('parr', 'Payment and refund request')]

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
                    ('RelatedGroup', 'Related Group'),
                    ('AssistantOfOffice', 'Executive Vice President'),
                    ('DeputyOfOffice', 'Senior Executive Vice President'),
                    ('SmallNote', 'Small Note'),
                    ('DirectorOfOffice', 'Director'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                    ('reject', 'Reject')]

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

APPROVE_POSITION = [('DirectorOfDepartment', 'Vice President/Director'),
                    ('RelatedGroup', 'Related Group'),
                    ('DirectorOfFinance', 'Division Manager of Finance, Accounting and Control Division'),
                    ('ManagerOfStock', 'Division Manager of General Affairs and Facilities Division'),
                    ('AssistantOfOffice', 'Executive Vice President'),
                    ('DeputyOfOffice', 'Senior Executive Vice President'),
                    ('SmallNote', 'Small Note'),
                    ('DirectorOfOffice', 'President/CEO')]

STATE_APPROVE = [('pending', 'Pending'),
                 ('approve', 'Approve'),
                 ('reject', 'Reject')]

STATE_RESIDUAL = [('no_residual', 'No Residual'), ('residual', 'Residual')]

# SUBSIDIZED_CHOICES = [
#     ('depa_digital_startup_fund', 'DEPA Digital Startup Fund'),
#     ('depa_digital_transformation_fund', 'DEPA Digital Transformation Fund'),
#     ('depa_digital_research_development_and_innovation_fund', 'DEPA Digital Research Development and Innovation Fund'),
#     ('depa_digital_event_and_marketing_fund', 'DEPA Digital Event And Marketing Fund'),
#     ('depa_digital_infrastructure_fund_for_government_and_public_investment', 'DEPA Digital Infrastructure Fund for Government & Public Investment'),
#     ('depa_digital_infrastructure_fund_for_private_investment', 'DEPA Digital Infrastructure Fund for Private Investment'),
#     ('depa_digital_manpower_fund', 'DEPA Digital Manpower Fund'),
#     ('depa_scholarship', 'DEPA Scholarship'),
#     ('depa_digital_transformation_fund_for_commmunity', 'DEPA Digital Transformation Fund for Community'),
#     ('other', 'Other'),
# ]


class fw_pfb_FS201(models.Model):
    _name = 'fw_pfb_fin_system_201'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority ASC, fin_date DESC, fin_no DESC'

    def date_by_adding_business_days(self, from_date, add_days):
        business_days_to_add = add_days
        current_date = from_date
        while business_days_to_add > 0:
            current_date += timedelta(days=1)
            weekday = current_date.weekday()
            if weekday >= 5:
                continue
            business_days_to_add -= 1
        return current_date

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
            approver = self.env['fw_pfb_fin_system_201_approver'].search(
                [('fin_id', '=', self.id), ('employee_user_id.id', '=', self._uid)])
            if len(approver) > 1:
                for ap in approver:
                    rights += ap.fin_position + ' , '
            else:
                rights = approver.fin_position

        else:
            rights = 'fin_user'
        self.approver_rights = rights
        if rights == 'director':
            self.is_director = True

    @api.depends('requester')
    def _check_is_requester(self):
        for rec in self:
            if rec._uid == rec.requester.user_id.id:
                rec.is_requester = True
            else:
                rec.is_requester = False

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

    @api.returns('self')
    def _is_canedit_financial_default(self):
        canedit_financial = False
        usrid = self._uid
        group_id = self.env['res.groups'].search([('name', 'like', 'Can Edit Financial Staff Verification')], limit=1)
        if group_id :
            if group_id.users :
                for i in group_id.users :
                    if i.id == usrid :
                        canedit_financial = True
        
        return canedit_financial

    # Fin system
    has_history = fields.Boolean(
        string="Has History", 
        default=False,
        copy=False,
    )

    priority = fields.Selection(PRIORITY, string='Priority', required=True)
    
    target_approver = fields.Char(string='Target Approver' )

    flow_template = fields.Many2one('fw_pfb_flow_template',
                                domain=[('type', '=', 'parr'),('data_activate', '=', True)],
                                string='Flow Template')

    fin_objective = fields.Many2one('fw_pfb_objective',
                                 string='Objective')
    fin_type = fields.Selection(FIN_TYPE, string='FIN Type', default="parr")

    participantas_quantity = fields.Char(string='Participantas Quantity', default="0")
    place = fields.Many2many("ir.attachment",
                                  "attachment_fin201_place_rel",
                                  "attachment_fin201_place_id",
                                  "attachment_id",
                                  string="Place")
    operation_date = fields.Many2many("ir.attachment",
                                  "attachment_fin201_operation_date_rel",
                                  "attachment_fin201_operation_date_id",
                                  "attachment_id",
                                  string="Operation Date")
    seminar_partcipants = fields.Many2many("ir.attachment",
                                  "attachment_fin201_seminar_rel",
                                  "attachment_fin201_seminar_id",
                                  "attachment_id",
                                  string="Seminar Partcipants")
    other = fields.Text(string='Other')
    estimate_output = fields.Text(string='Estimate')
    please_consider = fields.Selection(FIN_TYPE, string='Please Consider', default="parr")

    canedit_financial = fields.Boolean(string='Can Edit Financial Staff Verification',
                                  compute='_is_canedit_financial',
                                    default=_is_canedit_financial_default)

    fin_no = fields.Char(string='fin NO.',
                         readonly=True, )

    reference = fields.Char(string=_("Reference") )

    fin_date = fields.Date(string='fin Date',
                           default=lambda self: date.today(),
                           readonly=True)
    approved_amount = fields.Float(string='Approved amount')
    requester = fields.Many2one('hr.employee',
                                string='Requester',
                                default=_default_employee_get)
    is_requester = fields.Boolean(string='Is requester',
                                  compute='_check_is_requester')
    is_director = fields.Boolean(string="Is director",
                                 compute='_get_approver_rights')
    department = fields.Many2one('hr.department',
                                 string='Department',
                                 related='requester.department_id',)
    actual_department_name = fields.Char(string='Department',
                                         compute='_set_actual_department_name',)
    position = fields.Many2one('hr.job',
                               string='Position',
                               related='requester.job_id',
                               readonly=True)
    # emp_code = fields.Char(string='Employee code',
    #                        related='requester.es_employee_code',
    #                        readonly=True)
    state = fields.Selection(STATE_SELECTION,
                             default='draft',
                             required=True)
    subject = fields.Char(string='Subject')
    subject_to = fields.Char(string='Subject To.')
    objective = fields.Text(string='Objective')
    objective_changed = fields.Text(string='Objective changed')
    participants = fields.Many2many('hr.employee')
    template_id = fields.Many2many('sale.order.template',
                                   'so_template_fin_rel',
                                   'so_id',
                                   'fin_id',
                                   readonly=True,
                                   states={'draft': [('readonly', False)]},
                                   domain=[('fin_ok', '=', True)])
    fin_lines = fields.One2many('fw_pfb_fin_system_201_line',
                                'fin_id',
                                copy=True, )
    is_fin_lock = fields.Boolean(string="Lock")
    fin_remark = fields.Text(string='Remark')

    request_amount_total = fields.Float(string='Request amount total', default=0)

    load_amount_total = fields.Float(string='Loan amount total', default=0)

    price_total = fields.Float(string='Total', compute='_compute_total')

    spent_amount_total  = fields.Float(string='Spent amount total', default=0)

    remaining_total  = fields.Float(string='Remaining amount paid / withdrawn', default=0)

    approver = fields.One2many('fw_pfb_fin_system_201_approver',
                               'fin_id',
                               copy=True,)
    approver_rights = fields.Char(string='Approver Rights',
                                  compute="_get_approver_rights")
    can_cancel = fields.Boolean(string='Can cancel',
                                compute='_check_can_cancel')
    show_fin = fields.Boolean(string='Show FIN', )
    check_reject = fields.Boolean(string='Check Reject')
    attachment = fields.Many2many("ir.attachment",
                                  "attachment_fin201_rel",
                                  "attachment_fin201_id",
                                  "attachment_id",
                                  string="Attachment")
    account_memo = fields.Text(string="Accounting Memo.")

    # Flag for check request_to_cancel was checked
    is_request_to_cancel = fields.Boolean(
        string='Is request to cancel?',
        default=False,
    )

    allowed_to_cancel = fields.Boolean(
        string='Allowed to cancel',
        default=False,
    )

    can_approve_to_cancel = fields.Boolean(
        string='Can approve to cancel',
        default=False,
        compute='_can_approve_to_cancel',
    )

    director_reject = fields.Boolean(
        default=False,
    )
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
    subsidized_measurement = fields.Many2many(
        'subsidized.measurement',
        'subsidized_measurement_fin_rel',
        'fin_201_id',
        'subsidized_measure_id',
        string='Subsidized Measurement',
    )
    subsidized_measurement_other = fields.Char(
        string='Subsidized Measurement Other',
    )
    other_subsidized_flag = fields.Boolean(
        string='Other Subsidized Flag',
    )

    @api.multi
    @api.onchange('fin_objective')
    def _onchange_fin_objective(self):
        for rec in self:
            rec.objective_changed = rec.fin_objective.description


    @api.multi
    @api.onchange('subsidized_measurement')
    def _onchange_subsidized_measurement(self):
        subsidized_measurement_list = []
        for rec in self:
            rec.other_subsidized_flag = False
            if rec.subsidized_measurement:
                for sm in rec.subsidized_measurement:
                    subsidized_measurement_list.append(sm.name)
                if 'Other' in subsidized_measurement_list:
                    rec.other_subsidized_flag = True
                else:
                    rec.other_subsidized_flag = False

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

    @api.multi
    def _can_approve_to_cancel(self):
        director_id = []
        for obj in self:
            director = self.env['fw_pfb_fin_settings2'].sudo().search([])
            for directoroffice in director.directorOfOffice.user_id:
                director_id.append(directoroffice.id)
            if self._uid in director_id:
                obj.can_approve_to_cancel = True

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, fin_date=date.today())
        res = super(fw_pfb_FS201, self).copy(default)
        if self.state == 'reject':
            res.has_history = True
            fin201_origin = self.id
            res.fin_set_to_draft_copy(fin201_origin)
        return res

    @api.multi
    def _set_actual_department_name(self):
        for record in self:
            record.actual_department_name = record.department.name

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        env_fin = self.env['fw_pfb_fin_system_201']
        env_fin_approver = self.env['fw_pfb_fin_system_201_approver']
        params = self._context.get('params')

        checkRule = False

        if params :
            if "action" in params :
                if params["action"] == 1131 :
                   checkRule = True
        
        res = super(fw_pfb_FS201, self).fields_view_get(
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
    def fin201_history(self):
        history_ids = self.env['fw_pfb_fin_system_201_history'].search([('fin201_origin','=',self.id)])

        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('fin_system.fin_system_201_request_history_action')
        list_view_id = imd.xmlid_to_res_id('fin_system_201_request_history_tree_view')
        form_view_id = imd.xmlid_to_res_id('fin_system_201_request_history_form_view')

        newcontext = eval(action.context).copy()

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': '%s' % newcontext,
            'res_model': action.res_model,
        }

        if len(history_ids) >= 1:
            result['domain'] = "[('id','in',%s)]" % [x.id for x in history_ids]
        else:
            result['domain'] = "[('id','=',0)]"

        return result

    @api.multi
    @api.depends('fin_lines.price_subtotal')
    def _compute_total(self):
        print('FIN201._compute_total - extension')
        for fin in self:
            fin.objective = False
            fin.approved_amount = 0

            fin.request_amount_total = 0
            fin.load_amount_total = 0
            fin.price_total = 0

            fin.remaining_total = 0

            for i in fin.fin_lines :
                if i.objective :
                    fin.objective = i.objective
                    
                if i.price_subtotal :
                    print('FIN approved_amount')
                    print(fin.approved_amount)
                    fin.approved_amount = fin.approved_amount + i.price_subtotal
                    fin.request_amount_total = fin.approved_amount

                if i.loan_amount :
                    fin.load_amount_total = fin.load_amount_total + i.loan_amount

                if i.payment_amount :
                    fin.price_total = fin.price_total + i.payment_amount

            fin.remaining_total = fin.load_amount_total - fin.spent_amount_total
            


    @api.onchange('fin_lines')
    def onchange_fin_lines(self):

        # self.objective = False
        self.approved_amount = 0

        self.request_amount_total = 0
        self.load_amount_total = 0
        self.price_total = 0
        self.remaining_total = 0

        for i in self.fin_lines :
            # if i.objective :
            #     self.objective = i.objective
                
            if i.price_subtotal :
                self.approved_amount = self.approved_amount + i.price_subtotal
                self.request_amount_total = self.approved_amount
                self.rat = self.request_amount_total

            if i.loan_amount :
                self.load_amount_total = self.load_amount_total + i.loan_amount
                self.lat = self.load_amount_total

            if i.payment_amount :
                self.price_total = self.price_total + i.payment_amount
                self.pt = self.price_total


        # self.remaining_total = self.load_amount_total - self.spent_amount_total
        # self.rt = self.remaining_total

        

    @api.onchange('spent_amount_total')
    def onchange_spent_amount_total(self):
        self.remaining_total = self.load_amount_total - self.spent_amount_total

    @api.multi
    def name_get(self):
        return [(cat.id, cat.fin_no) for cat in self]

    @api.multi
    def update_to_fin100(self):
        if self.fin_lines :
            for line in self.fin_lines :
                if line.fin_line_id :
                    data2 = {
                        "wiz_id" : line.fin_line_id,
                        "fin_date" : self.fin_date,
                        "fin201_id" : str( self.id ),
                        "fin201_line_id" : line.id,
                        "product_id" : line.product_id.id,
                        "description" : line.description,
                        "status" : self.state
                    }
                    fin100_line_id = self.env['fw_pfb_fin_system_100_line'].browse( int( line.fin_line_id ) )
                    if fin100_line_id :
                        item201 = self.env['fin100_line_all_fin201_item'].search( [ ("fin201_line_id", "=", str( line.id )) ], limit=1 )
                        if item201 :
                            item201.write( data2 )
                        else :
                            fin100_line_id.item_fin201_ids.create( data2 )
        return True

    @api.model
    def create(self, vals):
        vals['fin_no'] = self.env['ir.sequence'].next_by_code('seq_fw_pfb_fin_201')
        if "approver" in vals :
            for ap in vals["approver"] :
                if len(ap) == 3 :
                    datas = ap[2]
                    if "approve_active" in datas :
                        if datas["approve_active"] == True :
                            if "employee_id" in datas :
                                if "employee_id" in datas:
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
        res = super(fw_pfb_FS201, self).create(vals)

        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # res.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "Create FIN201",
        #         str(res.create_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "Create FIN201", res.create_date)
        res.message_post(body=_(log_message))

        return res
    
    @api.multi
    def write(self, vals):
        user_price = 0

        request_amount_total = 0
        load_amount_total = 0
        price_total = 0

        if "spent_amount_total" in vals :
            user_price = vals["spent_amount_total"]
        
        black_list = []
        if "fin_lines" in vals :
            for b in vals["fin_lines"] :
                status = b[0]
                bid = b[1]
                datas = b[2]

                if status == 2 :
                    black_list.append( int( bid ) )
                elif status == 1 :
                    fl = self.env['fw_pfb_fin_system_201_line'].browse( int( bid ) )
                    if fl :
                        fl.write( datas )

        
        finlines = self.env['fw_pfb_fin_system_201_line'].search([('fin_id','=',self.id)])
        if finlines :
            for i in finlines :
                if not int(i.id) in black_list:
                    if i.price_subtotal :
                        request_amount_total += i.price_subtotal
                    if i.loan_amount :
                        load_amount_total += i.loan_amount
                    if i.payment_amount :
                        price_total += i.payment_amount
        
        vals['request_amount_total'] = request_amount_total
        vals['load_amount_total'] = load_amount_total
        vals['price_total'] = price_total
        # vals['remaining_total'] = load_amount_total - user_price

        return super(fw_pfb_FS201, self).write(vals)

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
            elif "RelatedGroup" in list :
                targetApprover = 'RelatedGroup'
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
    def fin_complete(self):
        self.write({
            'state': 'completed',
            'target_approver' : False
        })
        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # self.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "Complete FIN201",
        #         str(self.write_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "Complete FIN201", self.write_date)
        self.message_post(body=_(log_message))

        return True

    @api.multi
    def fin_request_to_cancel(self):
        self.write({
            'is_request_to_cancel': True,
        })
        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # self.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "Request to Cancel",
        #         str(self.write_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "Request to Cancel", self.write_date)
        self.message_post(body=_(log_message))
        return True

    @api.multi
    def action_approve_to_cancel(self):
        self.write({
            'allowed_to_cancel': True,
        })
        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # self.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "Approve to Cancel",
        #         str(self.write_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "Approve to Cancel", self.write_date)
        self.message_post(body=_(log_message))
        return True

    @api.multi
    def fin_cancel(self):
        self.write({
            'state': 'cancelled',
            'allowed_to_cancel': False,
            'can_approve_to_cancel': False,
            'is_request_to_cancel': False
        })
        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # self.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "FIN201 Cancel",
        #         str(self.write_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "FIN201 Cancel", self.write_date)
        self.message_post(body=_(log_message))

        return True

    @api.multi
    def fin_set_to_draft_copy(self, fin201_origin):
        #issue #292  copy function from fin_set_to_draft add value fin201_origin
        # Create History data
        f100h = self.env['fw_pfb_fin_system_201_history'].search([('fin201_origin', '=', fin201_origin)])
        data_fin201_origin = self.env['fw_pfb_fin_system_201'].browse(fin201_origin)
        countHistory = 0

        if f100h:
            countHistory = len(f100h)

        datas = {
            "name": "Reject FIN201 No." + data_fin201_origin.fin_no + " / " + str(countHistory + 1),
            "fin_no": "Reject FIN201 No." + data_fin201_origin.fin_no + " / " + str(countHistory + 1),
            "fin201_origin": self.id,
            "fin_type": self.fin_type,
            "fin_date": self.fin_date,
            "subject": self.subject,
            "subject_to": self.subject_to,
            "objective": self.objective,
            "participantas_quantity": self.participantas_quantity,
            "other": self.other,
            "estimate_output": self.estimate_output,
            "please_consider": self.please_consider,
            "fin_remark": self.fin_remark,
            "is_fin_lock": self.is_fin_lock,
            "state": self.state,
            "price_total": self.price_total,
            "priority": self.priority
        }
        if self.requester:
            datas["requester"] = self.requester.id
        if self.department:
            datas["department"] = self.department.id
        if self.fin_objective:
            datas["fin_objective"] = self.fin_objective.id

        temp = ""
        if self.template_id:
            for i in self.template_id:
                if temp != "":
                    temp += ", "
                temp += i.name
            datas["template_id"] = temp

        if self.flow_template:
            datas['flow_template'] = self.flow_template.id

        hid = self.env['fw_pfb_fin_system_201_history'].create(datas)

        for each in self.fin_lines:
            data = {
                "fin_id": hid.id,
                "description": each.description,
                "product_uom": each.product_uom.id,
                "product_uom_qty": each.product_uom_qty,
                "price_unit": each.price_unit,
                "price_subtotal": each.price_subtotal,
                "product_id": each.product_id.id,
                "projects_and_plan": each.projects_and_plan.id
            }
            self.env['fw_pfb_fin_system_201_line_history'].create(data)

        for each in self.approver:
            data = {
                "fin_id": hid.id,
                "position_index": each.position_index,
                "employee_id": each.employee_id.id,
                "fin_position": each.fin_position,
                "approve_position": each.approve_position,
                "action_date": each.action_date,
                "state": each.state,
                "memo": each.memo,
            }
            self.env['fw_pfb_fin_system_201_approver_history'].create(data)
        # END Create History data

        self.fin_date = date.today()
        self.can_approve_to_cancel = False
        self.allowed_to_cancel = False
        self.is_request_to_cancel = False

        for approver in self.approver:
            approver.write({
                'memo': '',
                'action_date': None,
                'state': 'pending',
            })
        self.write({
            'state': 'draft',
            'target_approver': False,
            'check_reject': False,
        })
        log_message = fin_middleware.message_log_stamp(self, "FIN201 Set to Draft", self.write_date)
        self.message_post(body=_(log_message))
        return True
    @api.multi
    def fin_set_to_draft(self):

        # Create History data
        f100h = self.env['fw_pfb_fin_system_201_history'].search([('fin201_origin', '=', self.id)])
        countHistory = 0

        if f100h :
            countHistory = len( f100h )

        datas = {
            "name" : "Reject FIN201 No." + self.fin_no + " / " + str( countHistory + 1 ),
            "fin_no" : "Reject FIN201 No." + self.fin_no + " / " + str( countHistory + 1 ),
            "fin201_origin" : self.id,
            "fin_type" : self.fin_type,
            "fin_date" : self.fin_date,
            "subject" : self.subject,
            "subject_to" : self.subject_to,
            # "fin_ref" : self.fin_ref,
            "objective" : self.objective,
            "participantas_quantity" : self.participantas_quantity,
            "other" : self.other,
            "estimate_output" : self.estimate_output,
            "please_consider" : self.please_consider,
            "fin_remark" : self.fin_remark,
            "is_fin_lock" : self.is_fin_lock,
            "state" : self.state,
            "price_total" : self.price_total,
            "priority" : self.priority
        }
        if self.requester :
            datas["requester"] = self.requester.id
        if self.department :
            datas["department"] = self.department.id
        if self.fin_objective :
            datas["fin_objective"] = self.fin_objective.id

        temp = ""
        if self.template_id :
            for i in self.template_id :
                if temp != "" :
                    temp += ", "
                temp += i.name
            datas["template_id"] = temp
        
        if self.flow_template:
            datas['flow_template'] = self.flow_template.id

        # if self.flow_template_eroe :
        #     datas["flow_template"] = self.flow_template_eroe.id
        # elif  self.flow_template_erob :
        #     datas["flow_template"] = self.flow_template_erob.id
        # elif  self.flow_template_proo :
        #     datas["flow_template"] = self.flow_template_proo.id

        hid = self.env['fw_pfb_fin_system_201_history'].create( datas )

        for each in self.fin_lines :
            data = {
                    "fin_id" : hid.id,
                    "description" : each.description,
                    "product_uom" : each.product_uom.id,
                    "product_uom_qty" : each.product_uom_qty,
                    "price_unit" : each.price_unit,
                    "price_subtotal" : each.price_subtotal,
                    "product_id" : each.product_id.id,
                    "projects_and_plan" : each.projects_and_plan.id
                }
            self.env['fw_pfb_fin_system_201_line_history'].create( data )

        for each in self.approver :
            data = {
                    "fin_id" : hid.id,
                    "position_index" : each.position_index,
                    "employee_id" : each.employee_id.id,
                    "fin_position" : each.fin_position,
                    "approve_position" : each.approve_position,
                    "action_date" : each.action_date,
                    "state" : each.state,
                    "memo" : each.memo,
                }
            self.env['fw_pfb_fin_system_201_approver_history'].create( data )
        # END Create History data
            

        self.fin_date = date.today()
        self.can_approve_to_cancel = False
        self.allowed_to_cancel = False
        self.is_request_to_cancel = False

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
        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # self.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "FIN201 Set to Draft",
        #         str(self.write_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "FIN201 Set to Draft", self.write_date)
        self.message_post(body=_(log_message))
        return True

    @api.multi
    def fin_lock(self):
        self.write({
            'is_fin_lock': True
        })
        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # self.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "FIN201 Lock",
        #         str(self.write_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "FIN201 Lock", self.write_date)
        self.message_post(body=_(log_message))
        return True

    @api.multi
    def fin_unlock(self):
        self.write({
            'is_fin_lock': False
        })
        # Stamp Log
        # employee_obj = self.env['hr.employee'].search([
        #     ('user_id', '=', self._uid),
        # ])
        # if employee_obj:
        #     user_name = _("%s" % employee_obj.name)
        # else:
        #     user_obj = self.env['res.users'].search([
        #         ('id', '=', self._uid),
        #     ])
        #     user_name = _("%s" % user_obj.name)
        # self.message_post(
        #     body=_("<b><u>%s</u></b><br />%s : <b>%s</b><br />Action : %s <br />Date/Time : %s" % (
        #         "SYSTEM LOG",
        #         "Employee" if employee_obj else "User",
        #         str(user_name),
        #         "FIN201 Unlock",
        #         str(self.write_date),
        #     ))
        # )
        log_message = fin_middleware.message_log_stamp(self, "FIN201 Unlock", self.write_date)
        self.message_post(body=_(log_message))
        return True

    @api.multi
    def button_request_fin100(self):
        # create wizard
        self.write({})
        newid = self.env['fin_201_request_101_wiz'].create({})
        return {
                'name': "FIN100 Requests",
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'fin_201_request_101_wiz',
                'view_id': self.env.ref('fin_system.fin_201_request_101_wiz_form').id,
                'res_id':newid.id,
                'type': 'ir.actions.act_window',
                'target': 'new'
          }

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


class fw_pfb_FS201Lines(models.Model):
    _name = 'fw_pfb_fin_system_201_line'

    @api.one
    def _compute_price_all_fin401(self):
        for rec in self :
            total = 0
            lines = self.env["fw_pfb_fin_system_401_line"].search( [("fin_line_id", "=", rec.fin_line_id )] )
            if lines :
                for line in lines :
                    total += line.lend
                
                rec.price_all_fin401 = total

    @api.depends('price_unit', 'product_uom_qty')
    def _compute_subtotal(self):
        for line in self:
            line['price_subtotal'] = line.product_uom_qty * line.price_unit

    @api.onchange('product_id')
    def _set_price(self):
        # self.price_unit = self.product_id.product_tmpl_id.standard_price
        # self.product_uom = self.product_id.product_tmpl_id.uom_id
        self.price_unit = self.product_id.standard_price
        self.product_uom = self.product_id.uom_id

    fin_type = fields.Selection(FIN_TYPE_ON_FIN100, string='FIN Type')
    fin_id = fields.Many2one('fw_pfb_fin_system_201',
                             required=True,
                             ondelete='cascade',
                             index=True,
                             copy=False)
    objective = fields.Text(string='Objective')
    fin100_number = fields.Many2one('fw_pfb_fin_system_100',string=_("FIN100 number"))
    fin_line_id = fields.Char(string='Fin line id' )
    product_id = fields.Many2one('product.template',
                                 domain=[('fin_ok', '=', True)],
                                 required=True)
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

    loan_amount = fields.Float(string='Loan amount')
    payment_amount = fields.Float(string='Payment amount', default = 0)

    price_all_fin401 = fields.Float('Price All Fin401', compute="_compute_price_all_fin401")
    pay_amount =  fields.Float('Pay', default = 0)

    @api.multi
    def unlink(self):
        for rec in self :
            strId = str(rec.id)
            lineF201 = self.env["fin100_line_all_fin201_item"].search([("fin201_line_id", "=" , strId )])
            if lineF201 : 
                lineF201.unlink()

            return super(fw_pfb_FS201Lines, self).unlink()


class fw_pfb_FS100RequestToCancelWizard(models.TransientModel):
    _name = 'wizard.fw_pfb_fin_system_201_request_to_cancel_request'

    memo = fields.Text(
        'Memo',
        required=True
    )

    @api.multi
    def confirm_to_request_to_cancel_fin_201(self):
        context = self._context
        if 'fw_pfb_fin_system_201' == context['active_model']:
            fin201 = self.env['fw_pfb_fin_system_201'].search([
                ('id', '=', context['active_id'])
            ])
            if fin201:
                fin201.is_request_to_cancel = True
                fin201.cancel_reason = self.memo
                # fin201.message_post(
                #     body=_(
                #         "Action : %s <br />Date/Time : %s" % (
                #         "Request To Cancel",
                #         str(fin201.write_date),
                #     ))
                # )

                log_message = fin_middleware.message_log_stamp(self, "Request To Cancel", fin201.write_date)
                fin201.message_post(body=_(log_message))
                # fin100.message_post(body=_("ACTION : Request To Cancel<br /> Message : %s"%(self.memo)))


class fw_pfb_FS201ApproveToCancelWizard(models.TransientModel):
    _name = 'wizard.fw_pfb_fin_system_201_request_to_cancel'

    memo = fields.Text('Memo',
                       required=True)

    @api.multi
    def approve_to_cancel_fin_201(self):
        context = self._context
        if 'fw_pfb_fin_system_201' == context['active_model']:
            fin201 = self.env['fw_pfb_fin_system_201'].search([
                ('id', '=', context['active_id'])
            ])
            if fin201:
                fin201.allowed_to_cancel = True
                # fin201.message_post(
                #     body=_(
                #         "Action : %s <br />Date/Time : %s" % (
                #         "Approve To Cancel",
                #         str(fin201.write_date),
                #     ))
                # )
                log_message = fin_middleware.message_log_stamp(self, "Approve to Cancel", fin201.write_date)
                fin201.message_post(body=_(log_message))


    @api.multi
    def reject_to_cancel_fin_201(self):
        context = self._context
        if 'fw_pfb_fin_system_201' == context['active_model']:
            fin201 = self.env['fw_pfb_fin_system_201'].search([
                ('id', '=', context['active_id'])
            ])
            if fin201:
                fin201.director_reject = True
                fin201.message_post(
                    body=_(
                        "Action : %s <br />Date/Time : %s" % (
                        "Reject To Cancel",
                        str(fin201.write_date),
                    ))
                )


class fw_pfb_FS201Approver(models.Model):
    _name = 'fw_pfb_fin_system_201_approver'
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
    approve_position = fields.Selection(APPROVE_POSITION, string='Approve Position', required=True)
    employee_line = fields.One2many('fw_pfb_approve_employee_list201', 'release_id', string='Please select employee')
    need_to_change_employee = fields.Boolean(string='Need to change employee', default=False)

    fin_id = fields.Many2one('fw_pfb_fin_system_201',
                             required=True,
                             ondelete='cascade',
                             index=True,
                             copy=False)
    employee_id = fields.Many2one('hr.employee',
                                  required=True,
                                  domain=[('user_id', '!=', None),
                                          ('fin_can_approve', '=', True)])
    fin_position = fields.Selection(FIN_SELECTION, string='FIN Position')
    employee_user_id = fields.Many2one('res.users',
                                       related='employee_id.user_id',
                                       readonly=True, )
    action_date = fields.Datetime(string='Action Date', copy=False)
    state = fields.Selection(STATE_APPROVE,
                             string='State approve',
                             default='pending')
    memo = fields.Text(string='Memo', copy=False)
    show_fin = fields.Boolean(string='Show FIN',
                              compute=_show_fin)

    @api.model
    def create(self, vals):
        vals["need_to_change_employee"] = False
        vals["employee_line"] = False
        return super(fw_pfb_FS201Approver, self).create(vals)

    @api.multi
    def write(self, vals):
        vals["need_to_change_employee"] = False
        vals["employee_line"] = False
        # if self.objective is not None:
        #     vals['objective'] = self.objective
        return super(fw_pfb_FS201Approver, self).write(vals)


class fw_pfb_FS201ApproveWizard(models.TransientModel):
    _name = 'wizard.fw_pfb_fin_system_201_approver'

    memo = fields.Text('Memo', required=True)

    @api.multi
    def approve_fin_201(self):
        context = self._context
        if context:
            approver_obj = self.env['fw_pfb_fin_system_201_approver'].search([('id', '=', context['active_id'])])
            if approver_obj.state != 'DirectorOfOffice' : 
                if approver_obj.approve_position == 'DirectorOfDepartment':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'
                    related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                        ('approve_active', '=', True),
                        ('approve_position', '=', 'DirectorOfDepartment')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'DirectorOfDepartment')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'DirectorOfDepartment'
                            approver_obj.fin_id.target_approver = 'RelatedGroup'

                elif approver_obj.approve_position == 'RelatedGroup' :
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'RelatedGroup')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
                            ('fin_id', '=', approver_obj.fin_id.id),
                            ('state', '=', 'approve'),
                            ('approve_active', '=', True),
                            ('approve_position', '=', 'RelatedGroup')
                        ])

                        if len(related_obj) == len(check_related_obj):
                            approver_obj.fin_id.state = 'RelatedGroup'
                            approver_obj.fin_id.target_approver = 'AssistantOfOffice'                
                
                elif approver_obj.approve_position == 'AssistantOfOffice':
                    approver_obj.memo = self.memo
                    approver_obj.action_date = datetime.now()
                    approver_obj.state = 'approve'

                    related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'AssistantOfOffice')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
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

                    related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'DeputyOfOffice')
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
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

                    related_obj = self.env['fw_pfb_fin_system_201_approver'].search([
                        ('fin_id', '=', approver_obj.fin_id.id),
                            ('approve_active', '=', True),
                        ('approve_position', '=', 'SmallNote'),
                    ])

                    if len(related_obj) >= 1:
                        check_related_obj= self.env['fw_pfb_fin_system_201_approver'].search([
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
                        if targetApprover not in list :
                            if targetApprover == "RelatedGroup" :
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
    def reject_fin_201(self):
        context = self._context
        if context:
            approver_obj = self.env['fw_pfb_fin_system_201_approver'].search([('id', '=', context['active_id'])])
            approver_obj.memo = self.memo
            approver_obj.action_date = datetime.now()
            approver_obj.state = 'reject'
            approver_obj.fin_id.check_reject = True
            approver_obj.fin_id.has_history = True
            approver_obj.fin_id.state = "reject"
            #raise UserError(_('You can not do Reject'))
        res = {'type': 'ir.actions.client', 'tag': 'reload'}
        return res

class fw_pfb_approve_employee_list(models.TransientModel):
    _name = 'fw_pfb_approve_employee_list201'

    release_id = fields.Many2one('fw_pfb_fin_system_201_approver')

    data_activate = fields.Boolean(string='Active')
    name = fields.Many2one('hr.employee', string='Employee Name')


class SubsidizedMeasurement(models.Model):
    _name = 'subsidized.measurement'

    name = fields.Char(
        string='Name',
        required=True,
    )
