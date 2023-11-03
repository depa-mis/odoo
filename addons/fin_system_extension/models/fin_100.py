# -*- coding: utf-8 -*-
# ProThai Technology Co., Ltd.


from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from random import randrange
import odoo.addons.fin_system.models.fin_100 as ORIG_FIN100
import collections
from lxml import etree
from odoo.addons.fin_system.models.fin_middleware import message_log_stamp

RETURN_STATE = [
    'cancelled',
    'reject'
]
# Step 3 for FIN100, Step 2 for FIN201 & FIN401
BYPASS_FIN_STEP_TO_DIRECTOR = 3


class fw_pfb_FS100(models.Model):
    _inherit = 'fw_pfb_fin_system_100'
    _rec_name = "fin_no"

    priority = fields.Selection(default="1_normal") # set default=normal
    fin_projects = fields.One2many('fw_pfb_fin_system_100_projects', 'fin_id', copy=True, readonly=False) # set readonly=False
    trigger = fields.Integer(string="trigger")

    next_approval_id = fields.Many2one('fw_pfb_fin_system_100_approver', string='Next Approval', compute='_compute_next_approval', store=True)
    next_approval_ids = fields.Many2many('fw_pfb_fin_system_100_approver', string='Next Approval IDS',
        relation="fin100_approval_approver_rel", column1='fin100_id', column2='approval_id', compute='_compute_next_approval', store=True)
    next_approval_user_ids = fields.Many2many('res.users', string='Next Approval Users',
        relation="fin100_approval_res_users_rel", column1='fin100_id', column2='user_id', compute='_compute_next_approval', store=True)
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')

    next_comment_ids = fields.Many2many('fw_pfb_fin_system_100_approver', string='Next Comment', 
        relation="fin100_approval_comment_rel", column1='fin100_id', column2='approval_id', compute='_compute_next_comment', store=True)
    next_comment_user_ids = fields.Many2many('res.users', string='Next Comment Users',
        relation="fin100_comment_res_users_rel", column1='fin100_id', column2='user_id', compute='_compute_next_comment', store=True)
    can_comment = fields.Boolean('Can Comment', compute='_compute_can_comment')

    has_project = fields.Boolean('Has Project', compute='_compute_has_project')
    lock = fields.Boolean('MASTER LOCK', compute="_compute_lock")
    fin_lines_to_edit = fields.One2many('fw_pfb_fin_system_100_line', 'fin_id', related="fin_lines", string="Fin Lines to Edit")
    can_complete = fields.Boolean('Can Complete', compute='_compute_can_complete')

    # To use with check availability button to check FIN100 is newly create
    is_new = fields.Boolean(default=True)
    check_availability_button = fields.Boolean('Check Availability')
    
    # To use with check availability button when line changed
    is_line_changed = fields.Boolean(default=False)

    waiting_line_ids = fields.One2many(
        'waiting.fin.system.100.line',
        'fin_id',
        string='FIN 100 waiting line',
        copy=False,
    )

    # Sarabun
    saraban_document_ids = fields.Many2many(
        'document.internal.main',
        'fin100_internal_document_rel',
        'fin_id',
        'fin_internal_document_id',
        string='หนังสือภายใน'
    )

    saraban_receive_ids = fields.Many2many(
        'receive.document.main',
        'fin100_receive_document_rel',
        'fin_id',
        'fin_internal_document_id',
        string='หนังสือรับ'
    )

    def migrate_fin_approval_to_new_flow_director_by_id(self, fin_id=None):
        fin100_obj_list = self.env['fw_pfb_fin_system_100'].search([
                        ('id', '=', fin_id),
                        ('state', '=', 'DirectorOfOffice')
                    ])
        for fin100 in fin100_obj_list:
            fin100.waiting_line_ids = False
            pending_approver = fin100.approver.filtered(lambda l: (l.approve_active and l.state == 'pending') or (l.approve_active and l.state != 'waiting' and not l.memo and not l.action_date))
            if pending_approver:
                for pending in pending_approver:
                    pending.state = 'waiting'

            active_step = fin100.approver.filtered(lambda l: l.approve_active and l.state == 'approve')[-1]
            if active_step:
                fin100.state = active_step.approve_position
                comment_approver_obj = fin100.approver.filtered(lambda l: l.approve_active and l.approval_type == 'comment' and l.state == 'waiting' and l.approve_step == active_step.approve_step)
                current_step_waiting = fin100.approver.filtered(lambda l: l.approve_step == active_step.approve_step and l.approve_active and l.approval_type == 'mandatory' and l.state == 'waiting')
                if comment_approver_obj or current_step_waiting:
                    fin100._add_pending_to_step_approver_fin(active_step.approve_step)
                else:
                    step_list = [approver.approve_step for approver in fin100.approver.filtered(lambda l: l.approve_active)]
                    step_list = sorted(set(step_list))
                    # Get next step if there is no next step then last step (when next step = -1)
                    next_step = next(iter(filter(lambda l: l > active_step.approve_step, step_list)), -1)
                    if next_step != -1:
                        fin100._add_pending_to_step_approver_fin(next_step)
                    elif next_step == -1:
                        fin100.update({
                                "waiting_line_ids": False,
                                "state": 'DirectorOfOffice'
                            })
                fin100._check_comment_step_lower(active_step.approve_step)
                fin100._check_fin_waiting_with_approver()

    def migrate_fin_approval_to_new_flow(self):
        fin100_obj_list = self.env['fw_pfb_fin_system_100'].search([
                        ('state', 'not in', ['draft', 'sent', 'completed', 'cancelled', 'reject', 'DirectorOfOffice'])
                    ])
        for fin100 in fin100_obj_list:
            fin100.waiting_line_ids = False
            pending_approver = fin100.approver.filtered(lambda l: l.approve_active and l.state == 'pending')
            if pending_approver:
                for pending in pending_approver:
                    pending.state = 'waiting'

            active_step = fin100.approver.filtered(lambda l: l.approve_active and l.state == 'approve')[-1]
            if active_step:
                comment_approver_obj = fin100.approver.filtered(lambda l: l.approve_active and l.approval_type == 'comment' and l.state == 'waiting' and l.approve_step == active_step.approve_step)
                current_step_waiting = fin100.approver.filtered(lambda l: l.approve_step == active_step.approve_step and l.approve_active and l.approval_type == 'mandatory' and l.state == 'waiting')
                if comment_approver_obj or current_step_waiting:
                    fin100._add_pending_to_step_approver_fin(active_step.approve_step)
                else:
                    step_list = [approver.approve_step for approver in fin100.approver.filtered(lambda l: l.approve_active)]
                    step_list = sorted(set(step_list))
                    # Get next step if there is no next step then last step (when next step = -1)
                    next_step = next(iter(filter(lambda l: l > active_step.approve_step, step_list)), -1)
                    if next_step != -1:
                        fin100._add_pending_to_step_approver_fin(next_step)
                    elif next_step == -1:
                        fin100.update({
                                "waiting_line_ids": False,
                                "state": 'DirectorOfOffice'
                            })
                fin100._check_comment_step_lower(active_step.approve_step)
                fin100._check_fin_waiting_with_approver()

    def migrate_fin_approval_to_new_flow_by_id(self, fin_id=None):
        fin100_obj_list = self.env['fw_pfb_fin_system_100'].search([
                        ('id', '=', fin_id),
                        ('state', 'not in', ['draft', 'sent', 'completed', 'cancelled', 'reject', 'DirectorOfOffice'])
                    ])
        for fin100 in fin100_obj_list:
            fin100.waiting_line_ids = False
            pending_approver = fin100.approver.filtered(lambda l: l.approve_active and l.state == 'pending')
            if pending_approver:
                for pending in pending_approver:
                    pending.state = 'waiting'

            active_step = fin100.approver.filtered(lambda l: l.approve_active and l.state == 'approve')[-1]
            if active_step:
                comment_approver_obj = fin100.approver.filtered(lambda l: l.approve_active and l.approval_type == 'comment' and l.state == 'waiting' and l.approve_step == active_step.approve_step)
                current_step_waiting = fin100.approver.filtered(lambda l: l.approve_step == active_step.approve_step and l.approve_active and l.approval_type == 'mandatory' and l.state == 'waiting')
                if comment_approver_obj or current_step_waiting:
                    fin100._add_pending_to_step_approver_fin(active_step.approve_step)
                else:
                    step_list = [approver.approve_step for approver in fin100.approver.filtered(lambda l: l.approve_active)]
                    step_list = sorted(set(step_list))
                    # Get next step if there is no next step then last step (when next step = -1)
                    next_step = next(iter(filter(lambda l: l > active_step.approve_step, step_list)), -1)
                    if next_step != -1:
                        fin100._add_pending_to_step_approver_fin(next_step)
                    elif next_step == -1:
                        fin100.update({
                                "waiting_line_ids": False,
                                "state": 'DirectorOfOffice'
                            })
                fin100._check_comment_step_lower(active_step.approve_step)
                fin100._check_fin_waiting_with_approver()

    def migrate_fin_approval_to_new_flow_draft_and_sent(self):
        fin100_obj_list = self.env['fw_pfb_fin_system_100'].search([
                        ('state', 'in', ['draft', 'sent'])
                    ])
        for fin100 in fin100_obj_list:
            if fin100.approver:
                # set all approver to None
                for approver in fin100.approver:
                    approver.state = None
                fin100.waiting_line_ids = False
                approve_approver = fin100.approver.filtered(lambda l: l.approve_active and (l.memo or l.action_date))
                approver_obj = fin100.approver.filtered(lambda l: l.approve_active)
                if not approve_approver:
                    for approver in approver_obj:
                        approver.state = 'waiting'

                first_step = fin100.approver.filtered(lambda l: l.approve_active)[0].approve_step
                if first_step and fin100.state == 'sent':
                    fin100._add_pending_to_step_approver_fin(first_step)
                    fin100._check_comment_step_lower(first_step)
                    fin100._check_fin_waiting_with_approver()

    def migrate_fin_approval_to_new_flow_draft_and_sent_by_id(self, fin_id=None):
        fin100_obj_list = self.env['fw_pfb_fin_system_100'].search([
                        ('id', '=', fin_id),
                        ('state', 'in', ['draft', 'sent'])
                    ])
        for fin100 in fin100_obj_list:
            if fin100.approver:
                # set all approver to None
                for approver in fin100.approver:
                    approver.state = None
                fin100.waiting_line_ids = False
                approve_approver = fin100.approver.filtered(lambda l: l.approve_active and (l.memo or l.action_date))
                approver_obj = fin100.approver.filtered(lambda l: l.approve_active)
                if not approve_approver:
                    for approver in approver_obj:
                        approver.state = 'waiting'

                first_step = fin100.approver.filtered(lambda l: l.approve_active)[0].approve_step
                if first_step and fin100.state == 'sent':
                    fin100._add_pending_to_step_approver_fin(first_step)
                    fin100._check_comment_step_lower(first_step)
                    fin100._check_fin_waiting_with_approver()

    def action_wizard_fin100_approval(self):
        self.ensure_one()
        approval_type = False
        aprroval_step = 0
        approver_obj = self.waiting_line_ids.filtered(lambda l: l.employee_id.user_id.id == self._uid)
        if approver_obj:
            approver_obj = approver_obj[0]
            approval_type = approver_obj.approval_type
            approval_step = approver_obj.approval_step
            return {
                'name': "Make Approval Wizard",
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'wizard.fin100.approval',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': {
                    'default_approval_type': approval_type,
                    'default_approval_step': approval_step
                }
            }
        else:
            raise ValidationError(_('Not your turn'))


    @api.multi
    @api.onchange('fin_lines', 'fin_lines.projects_and_plan', 'fin_lines_to_edit', 'fin_lines_to_edit.projects_and_plan')
    def _onchange_is_line_changed(self):
        print('CHANGE')
        for record in self:
            record.fin_projects = None
            record.is_line_changed = True
            for line in record.fin_lines:
                line.amount_before_change = line.price_subtotal

    @api.multi
    @api.onchange('check_availability_button')
    def check_availability(self):
        projects_line = []
        projects_list = {}
        for record in self:
            if record.is_line_changed:
                record.is_line_changed = False
                for line in record.fin_lines:
                    if line.projects_and_plan:
                        project_obj = self.env['account.analytic.account'].search([
                            ('id', '=', line.projects_and_plan.id)
                        ])
                        for pl in project_obj:
                            if pl.id not in projects_list:
                                print(line.amount_before_change)
                                projects_reserve = (line.amount_before_change - line.price_subtotal) if (line.amount_before_change > line.price_subtotal) else (line.amount_before_change + line.price_subtotal)
                                projects_list[pl.id] = {
                                    'projects_and_plan': pl.id,
                                    'projects_residual': pl.budget_balance,
                                    'projects_reserve': projects_reserve,
                                    'projects_return': 0.0,
                                    # 'projects_residual_amount': pl.budget_balance - line.price_subtotal,
                                }
            else:
                for line in record.fin_lines:
                    if line.projects_and_plan:
                        project_obj = self.env['account.analytic.account'].search([
                            ('id', '=', line.projects_and_plan.id)
                        ])
                        for pl in project_obj:
                            if pl.id not in projects_list:
                                projects_list[pl.id] = {
                                    'projects_and_plan': pl.id,
                                    'projects_residual': pl.budget_balance,
                                    'projects_reserve': line.price_subtotal,
                                    'projects_return': 0.0,
                                    # 'projects_residual_amount': pl.budget_balance - line.price_subtotal,
                                }
                            else:
                                projects_list[pl.id]['projects_reserve'] += line.price_subtotal
                                # projects_list[pl.id]['projects_residual_amount'] += pl.budget_balance - line.price_subtotal
        if projects_list:
            if self.fin_projects:
                self.fin_projects = None
            for pld in projects_list:
                projects_line.append((0, False, {
                    'projects_and_plan': projects_list[pld]['projects_and_plan'],
                    'projects_residual': projects_list[pld]['projects_residual'],
                    'projects_reserve': projects_list[pld]['projects_reserve'],
                    'projects_return': 0.0,
                    # 'projects_residual_amount': projects_list[pld]['projects_residual_amount'],
                }))
            self.update({
                'fin_projects': projects_line
            })


    @api.model
    def create(self, vals):
        res = super(fw_pfb_FS100, self).create(vals)
        res.is_new = False
        res.compute_line_project()
        return res

    def _compute_can_complete(self):
        print("FIN100._compute_can_complete",self)
        for fin100 in self:
            fin100.can_complete = False
            last_approval = fin100.approver and fin100.approver.sorted(lambda app: app.position_index)[-1] or False
            if last_approval:
                if self.env.user.id in last_approval.employee_user_id.ids:
                    fin100.can_complete = True
                else:
                    fin100.can_complete = False
                # force admin can complete
                if self.env.user.id == 1:
                    fin100.can_complete = True
            if fin100.is_fin_lock:
                fin100.can_complete = False

    @api.multi
    @api.depends('state', 'is_fin_lock', 'is_requester', 'is_director')
    def _compute_lock(self):
        for fin100 in self:
            con1 = fin100.state not in ['draft', 'DirectorOfOffice']
            con2 = fin100.is_fin_lock == True
            con3 = fin100.is_requester == False
            con4 = fin100.is_director == False
            con5 = fin100.has_project
            if (con1 or con2 or con3) and con4 and con5:
                fin100.lock = True
            else:
                fin100.lock = False
            print("FIN100._compute_lock", "(",con1, con2, con3,")", con4, con5, "---->", fin100.lock)
        return

    @api.multi
    @api.depends('fin_lines', 'fin_lines.projects_and_plan')
    def _compute_has_project(self):
        for fin100 in self:
            print("FIN100._compute_has_project", self)
            print(fin100.is_line_changed)
            has_project = True
            for line in fin100.fin_lines:
                if fin100.is_line_changed:
                    line.balance = line.price_subtotal
                if not line.projects_and_plan:
                    has_project = False
                    break
            fin100.has_project = has_project

    @api.multi
    @api.depends('state', 'approver',
        'approver.employee_id', 'approver.employee_id.user_id', 'approver.employee_user_id',
        'approver.action_date', 'approver.state', 'trigger')
    def _compute_next_approval(self):
        print("FIN100._compute_next_approval",self)
        for fin100 in self:
            if fin100.state == 'reject':
                fin100.next_approval_id = False
                return True
            latest_approval_ids = fin100.approver.filtered(lambda app: app.approval_type=='mandatory' and app.state=='approve' and app.approve_active==True)
            latest_approval = latest_approval_ids and latest_approval_ids[-1]
            if latest_approval:
                approval_ids_ready = fin100.approver\
                    .filtered(lambda app: app.approval_type=='mandatory' and app.position_index > latest_approval.position_index and app.state=='pending' and app.approve_active==True)
            else:
                approval_ids_ready = fin100.approver\
                    .filtered(lambda app: app.approval_type=='mandatory' and app.state=='pending' and app.approve_active==True)

            if approval_ids_ready:
                fin100.next_approval_id = approval_ids_ready[0]
                fin100.next_approval_ids = approval_ids_ready
                fin100.next_approval_user_ids = approval_ids_ready[0].mapped('employee_user_id')

            overrule_states = ['DirectorOfFinance','AssistantOfOffice','DeputyOfOffice','SmallNote']
            #overrule_states = []
            #for state in ORIG_FIN100.STATE_SELECTION:
                #if state[0] in ['draft','sent','completed','cancelled', 'reject']:
                    #continue
                #overrule_states.append(state[0])

            if fin100.state in overrule_states:
                #fin100.next_approval_user_ids |= fin100.approver.sorted(lambda app: app.position_index)[-1].mapped('employee_user_id')
                fin100.next_approval_user_ids |= fin100.approver\
                    .filtered(lambda app: app.approve_active==True)\
                    .sorted(lambda app: app.position_index)[-1].mapped('employee_user_id')

    @api.depends('next_approval_id', 'next_approval_user_ids', 'state', 'trigger')
    def _compute_can_approve(self):
        print("FIN100._compute_can_approve",self)
        for fin100 in self:
            #if self.env.user == fin100.next_approval_id.employee_user_id:
            if self.env.user in fin100.next_approval_user_ids:
                fin100.can_approve = True
            else:
                fin100.can_approve = False
            # force admin can approve
            if self.env.user.id == 1 and fin100.next_approval_user_ids:
                fin100.can_approve = True

    @api.multi
    @api.depends('state', 'approver', 'next_approval_id', 'trigger', 'approver.position_index', 'approver.approve_step',
        'approver.employee_id', 'approver.employee_id.user_id', 'approver.employee_user_id',
        'approver.action_date', 'approver.state', 'approver.approval_type')
    def _compute_next_comment(self):
        print("FIN100._compute_next_comment",self)
        for fin100 in self:
            approval_ids = self.env['fw_pfb_fin_system_100_approver']
            approval_ids |= fin100.approver\
                .filtered(lambda app: app.approve_active and app.approval_type=='comment' and app.approve_step <= fin100.next_approval_id.approve_step and (not app.state or app.state=='pending'))
            approval_ids |= fin100.approver.filtered(lambda app: app.approval_type=='comment') and fin100.approver.filtered(lambda app: app.approval_type=='comment')[-1]
            fin100.next_comment_ids = approval_ids.sorted(lambda app: app.position_index)
            if fin100.next_comment_ids:
                fin100.next_comment_user_ids = fin100.next_comment_ids.mapped('employee_user_id')

    @api.depends('next_comment_ids', 'next_comment_user_ids', 'next_comment_ids.employee_user_id', 'state', 'trigger')
    def _compute_can_comment(self):
        print("FIN100._compute_can_comment",self)
        for fin100 in self:
            if self.env.user in fin100.next_comment_user_ids:
                fin100.can_comment = True
            else:
                fin100.can_comment = False
            # force admin can approve
            if self.env.user.id == 1 and fin100.next_comment_user_ids:
                fin100.can_comment = True


    #to compute fin_projects when create fin_lines
    @api.multi
    def compute_line_project(self):
        print("compute_line_project",self)
        for obj in self:
            if obj.fin_projects:
                obj.fin_projects.unlink()
                obj.is_line_changed = False
            groups = {}
            for fin_line in obj.fin_lines:
                key = fin_line.fin_id, fin_line.projects_and_plan
                groups.setdefault(key, self.env['fw_pfb_fin_system_100_line'])
                groups[key] |= fin_line
            if groups:
                for (fin, project), fin_lines in groups.items():
                    amount_to_reserve = sum(fin_lines.mapped('price_subtotal')) or 0.0
                    residual_amount = project.budget_balance - amount_to_reserve
                    if fin.fin_type != 'eroe' and  residual_amount < 0 and not project.allow_negative:
                        raise ValidationError(_('Budget is not below zero (not allow negative amount)'))
                    else:
                        vals = {
                            'fin_id': fin.id,
                            'projects_and_plan': project.id,
                            'projects_reserve': amount_to_reserve,
                            'projects_residual': project.budget_balance,
                        }
                        line_proj = self.env['fw_pfb_fin_system_100_projects'].create(vals)
        return True

    @api.multi
    def write(self, vals):
        print("FIN100.write", self, vals)
        res = super(fw_pfb_FS100, self).write(vals)
        if 'fin_lines_to_edit' in vals:
            for line_edit in vals['fin_lines_to_edit']:
                if line_edit[2]:
                    if 'projects_and_plan' in line_edit[2]:
                        fin_line = self.env['fw_pfb_fin_system_100_line'].browse(line_edit[1])
                        fin_line.projects_and_plan = line_edit[2]['projects_and_plan']
        if 'fin_lines' in vals:
            self.compute_line_project()
        return res

    @api.onchange('flow_template_eroe', 'flow_template_erob', 'flow_template_proo')
    def _onchange_flow_template(self):
        print("FIN100._onchange_flow_template",self)
        self.approver = False
        template_id = False
        if self.flow_template_eroe :
            template_id = self.flow_template_eroe.id
        if self.flow_template_erob :
            template_id = self.flow_template_erob.id
        if self.flow_template_proo :
            template_id = self.flow_template_proo.id
        template = self.env['fw_pfb_flow_template'].browse(template_id)
        if template and template.approve_line:
            for line in template.approve_line:
                data = {
                    "approve_active": True if line.data_activate else False,
                    "employee_id" : line.emp_name.id,
                    "fin_position" : line.position,
                    "approve_active" : line.data_activate,
                    "approve_position" : line.approve_position,
                    "position_index" : line.position_index,
                    "approval_type" : line.approval_type,
                    "approve_step" : line.approve_step,
                    # "state": "waiting" if line.data_activate else None,
                }
                if line.data_activate :
                    data["state"] = "waiting"
                self.approver += self.approver.new(data)


    @api.multi
    def button_trigger(self):
        print("FIN100.button_trigger",self)
        for obj in self:
            obj.trigger = randrange(1000001)
            obj.approver.button_trigger()
            obj.fin_lines.button_trigger()
        return True

    # def _check_fin_for_pending_state(self):
    #     for rec in self:
    #         if not rec.waiting_line_ids:
    #             approver_list = rec.approver.filtered(lambda l: l.approve_active and l.approval_type == 'mandatory' and l.approve_step > bypass_fin_step_to_director)
    #             if approver_list:

    def _check_fin_waiting_with_approver(self):
        for rec in self:
            if not rec.waiting_line_ids:
                mandatory_approver_obj = rec.approver.filtered(lambda l: l.approve_active and l.approval_type == 'mandatory')
                mandatory_approve_obj = rec.approver.filtered(lambda l: l.approve_active and l.approval_type == 'mandatory' and l.state == 'approve')
                if len(mandatory_approve_obj) >= len(mandatory_approver_obj):
                    rec.state = 'completed'
                    rec.waiting_line_ids = False

    def _get_director(self):
        print('GET DIRECTOR')
        sign_employee = {}
        director = self.env['fw_pfb_fin_settings2'].sudo().search([])
        for directoroffice in director.directorOfOffice:
            sign_employee = directoroffice
        return sign_employee

    def _check_comment_step_lower(self, step):
        comment_approver_obj = self.approver.filtered(lambda l: l.approve_active and l.approval_type == 'comment' and l.approve_step < step and not l.action_date and not l.memo)
        if comment_approver_obj:
            for cao in comment_approver_obj:
                try:
                    cao.update({
                            'state': False
                        })
                    self.waiting_line_ids.filtered(lambda l: l.approval_step == cao.approve_step and l.employee_id.id == cao.employee_id.id).unlink()
                except:
                    pass

    @api.multi
    def _add_pending_to_step_approver_fin(self, step):
        fin100_obj = self
        approver_list_obj = fin100_obj.approver.filtered(lambda l: l.approve_active and l.approve_step == step)
        director = self._get_director()
        director_approve_obj = {}
        if step > BYPASS_FIN_STEP_TO_DIRECTOR:
            director_approve_obj = fin100_obj.approver.filtered(lambda l: l.employee_id.id == director.id and l.approve_active == True and l.state == 'waiting' and l.approve_step > BYPASS_FIN_STEP_TO_DIRECTOR)
        if approver_list_obj:
            for alo in approver_list_obj:
                if alo.approve_step == step and alo.state == 'waiting':
                    alo.state = 'pending'
        if director_approve_obj:
            director_approve_obj.state = 'pending'
        self._add_user_to_wait_list(step)

    @api.multi
    def action_set_approve(self, note="", employee_id=None, step=0):
        print("FIN100.action_set_approve",self)
        # self = FIN100 object
        director = self._get_director()
        director_approve_obj = {}
        director_approve_obj = self.approver.filtered(lambda l: l.employee_id.id == director.id and l.approve_active == True and l.state == 'pending' and l.approve_step > BYPASS_FIN_STEP_TO_DIRECTOR and l.employee_id.user_id.id == self._uid and director.user_id.id == self._uid)
        if step > BYPASS_FIN_STEP_TO_DIRECTOR and director_approve_obj:
            director_approve_obj.memo = note
            director_approve_obj.state = 'approve'
            director_approve_obj.user_id = self._uid
            director_approve_obj.action_date = datetime.now()
            self.state = 'completed'
            self.update({
                    'waiting_line_ids': False
                })
            all_approver = self.approver.search([
                    ('fin_id', '=', self.id),
                    ('approve_active', '=', True),
                    ('state', 'in', ['waiting', 'pending'])
                ])
            for aa in all_approver:
                aa.update({
                        'state': False
                    })
            
        else:
            # Get active approver
            approver_obj = self.approver.filtered(lambda l: l.approve_step == step and l.employee_id.user_id.id == self._uid and l.approve_active == True and l.approval_type == 'mandatory')
            approver_obj = approver_obj[0] if len(approver_obj) > 1 else approver_obj

            current_step_approver_count = len(self.approver.filtered(lambda l: l.approve_step == step and l.approve_active == True and l.approval_type == 'mandatory'))
            if approver_obj.employee_id.user_id.id == self._uid:
                # Set value
                approver_obj.memo = note
                approver_obj.state = 'approve'
                approver_obj.user_id = self._uid
                approver_obj.action_date = datetime.now()
                self.state = approver_obj.approve_position if approver_obj.approve_position != 'ManagerOfStock' else self.state
                # if approve success unlink from waiting list
                waiting_line_obj = self.waiting_line_ids.filtered(lambda l: l.employee_id.user_id.id == self._uid and l.approval_type == approver_obj.approval_type)
                try:
                    waiting_line_obj.unlink()
                except:
                    pass

                # check condition
                approver_count = len(self.approver.filtered(lambda l: l.approve_step == step and l.approve_active == True  and l.approval_type == 'mandatory' and l.state == 'approve'))

                if approver_count >= current_step_approver_count:
                    step_list = [approver.approve_step for approver in self.approver.filtered(lambda l: l.approve_active)]
                    step_list = sorted(set(step_list))
                    # Get next step if there is no next step then last step (when next step = -1)
                    next_step = next(iter(filter(lambda l: l > step, step_list)), -1)
                    if next_step != -1:
                        self._add_pending_to_step_approver_fin(next_step)
                    elif next_step == -1:
                        self.update({
                                "waiting_line_ids": False,
                                "state": 'DirectorOfOffice'
                            })
        self._check_comment_step_lower(step)
        self._check_fin_waiting_with_approver()

        
        # for fin100 in self:
        #     approval = fin100.next_approval_id
        #
        #     if self.env.user != approval.user_id:
        #         if self.env.user.id == 1:
        #             pass
        #         elif self.env.user in fin100.next_approval_user_ids:
        #             approval = fin100.next_approval_ids.filtered(lambda app: app.employee_id.user_id == self.env.user)
        #         else:
        #             raise UserError(_('Only authorized person to approve or action'))
        #
        #     if approval:
        #         if len(approval) > 1:
        #             approval = approval[0]
        #         if approval.approval_type == 'mandatory':
        #             pass
        #         if approval.approval_type == 'optional':
        #             pass
        #         if approval.approval_type == 'comment':
        #             raise UserError(_('Need to Comment'))
        #         approval.write({
        #             'state': 'approve',
        #             'action_date': fields.Datetime.now(),
        #             'user_id': self.env.uid,
        #             'memo': note,
        #         })
        #         approval.update_fin_status()
        #     else:
        #         latest_approval = fin100.approver.sorted(lambda app: app.position_index)[-1]
        #         if self.env.user == latest_approval.mapped('employee_user_id') and not latest_approval.approve_active:
        #             latest_approval.write({
        #                 'action_date': fields.Datetime.now(),
        #                 'user_id': self.env.uid,
        #                 'memo': note,
        #             })
        # return True

    @api.multi
    def action_set_reject(self, note="", employee_id=None, step=0):
        print("FIN100.action_set_reject",self)
        approver_obj = self.approver.filtered(lambda l: l.approve_step == step and l.employee_id.user_id.id == self._uid and l.approve_active == True and l.approval_type == 'mandatory')
        if approver_obj.employee_id.user_id.id == self._uid:
            # Set value
            approver_obj.memo = note
            approver_obj.state = 'reject'
            approver_obj.user_id = self._uid
            approver_obj.action_date = datetime.now()
            self.state = 'reject'
            self.update({
                    "waiting_line_ids": False,
                })
            current_aprrover = self.approver.filtered(lambda l: l.approve_active == True and l.state != ('approve', 'comment'))
            for ca in current_aprrover:
                ca.update({
                        'state': False
                    })
            # Recompute FIN projects and plan
            if self.fin_projects:
                for fin_project in self.fin_projects:
                    fin_project.projects_return = fin_project.projects_reserve
                    if fin_project.projects_and_plan:
                        # Recompute
                        fin_project.projects_and_plan.button_force_reset_fin100_lines()
                        fin_project.projects_and_plan.button_force_compute_fin100_lines()

        # for fin100 in self:
        #     approval = fin100.next_approval_id
        #     for approve in approval:
        #         print(approve)
        #
        #     if self.env.user != approval.user_id:
        #         if self.env.user.id == 1:
        #             pass
        #         elif self.env.user in fin100.next_approval_user_ids:
        #             approval = fin100.next_approval_ids.filtered(lambda app: app.employee_id.user_id == self.env.user)
        #         else:
        #             raise UserError(_('Only authorized person to approve or action'))
        #
        #     if approval:
        #         if len(approval) > 1:
        #             approval = approval[0]
        #         if approval.approval_type == 'mandatory':
        #             pass
        #         if approval.approval_type == 'optional':
        #             pass
        #         if approval.approval_type == 'comment':
        #             raise UserError(_('Need to Comment'))
        #         approval.write({
        #             'state': 'reject',
        #             'action_date': fields.Datetime.now(),
        #             'user_id': self.env.uid,
        #             'memo': note,
        #         })
        #         fin100.set_fin100_to_reject()
        #         fin100.action_generate_mail_to_reject()
        #     else:
        #         latest_approval = fin100.approver.sorted(lambda app: app.position_index)[-1]
        #         if self.env.user == latest_approval.mapped('employee_user_id') and not latest_approval.approve_active:
        #             latest_approval.write({
        #                 'action_date': fields.Datetime.now(),
        #                 'user_id': self.env.uid,
        #                 'memo': note,
        #             })
        #
        # if self.fin_projects:
        #     for fin_project in self.fin_projects:
        #         fin_project.projects_return = fin_project.projects_reserve
        #         if fin_project.projects_and_plan:
        #             # Recompute
        #             fin_project.projects_and_plan.button_force_reset_fin100_lines()
        #             fin_project.projects_and_plan.button_force_compute_fin100_lines()
        # return True

    @api.multi
    def action_set_comment(self, note="", employee_id=None, step=0):
        print("FIN100.action_set_comment",self)
        approver_obj = self.approver.filtered(lambda l: l.approve_step == step and l.employee_id.user_id.id == self._uid and l.approve_active == True and l.approval_type == 'comment')
        if approver_obj.employee_id.user_id.id == self._uid:
            # Set value
            approver_obj.memo = note
            approver_obj.state = 'comment'
            approver_obj.user_id = self._uid
            approver_obj.action_date = datetime.now()
            self.state = approver_obj.approve_position

            waiting_line_obj = self.waiting_line_ids.filtered(lambda l: l.employee_id.user_id.id == self._uid and l.approval_type == approver_obj.approval_type)
            try:
                waiting_line_obj.unlink()
            except:
                pass


            # check condition
            current_step_approver_count = len(self.approver.filtered(lambda l: l.approve_step == step and l.approve_active == True and l.approval_type == 'mandatory'))
            approver_count = len(self.approver.filtered(lambda l: l.approve_step == step and l.approve_active == True  and l.approval_type == 'mandatory' and l.state == 'approve'))

            if approver_count >= current_step_approver_count:
                step_list = [approver.approve_step for approver in self.approver.filtered(lambda l: l.approve_active and not l.memo and not l.action_date)]
                step_list = sorted(set(step_list))
                # Get next step if there is no next step then last step (when next step = -1)
                next_step = next(iter(filter(lambda l: l > step, step_list)), -1)
                if next_step != -1:
                    self._add_pending_to_step_approver_fin(next_step)
                elif next_step == -1:
                    self.update({
                            "waiting_line_ids": False,
                            "state": 'DirectorOfOffice'
                        })

        self._check_comment_step_lower(step)
        self._check_fin_waiting_with_approver()
            # check condition
            # step_list = [approver.approve_step for approver in self.approver.filtered(lambda l: l.approve_active)]
            # step_list = sorted(set(step_list))
            # # Get next step if there is no next step then last step (when next step = -1)
            # next_step = next(iter(filter(lambda l: l > step, step_list)), -1)
            # if next_step != -1:
            #     self._add_pending_to_step_approver_fin(next_step)
            # elif next_step == -1:
            #     self.update({
            #             "waiting_line_ids": False,
            #             "state": 'DirectorOfOffice'
            #         })

        # for fin100 in self:
        #     approval = fin100.next_comment_ids and fin100.next_comment_ids[0] or False
        #
        #     if self.env.user != approval.user_id:
        #         if self.env.user.id == 1:
        #             pass
        #         elif self.env.user in fin100.next_comment_user_ids:
        #             approval = fin100.next_comment_ids.filtered(lambda app: app.employee_id.user_id == self.env.user)
        #         else:
        #             raise UserError(_('Only authorized person to comment or action'))
        #
        #     if approval:
        #         if len(approval) > 1:
        #             approval = approval[0]
        #         if approval.approval_type == 'mandatory':
        #             raise UserError(_('Need to Approve / Reject'))
        #         if approval.approval_type == 'optional':
        #             pass
        #         if approval.approval_type == 'comment':
        #             pass
        #         if not note:
        #             raise UserError(_('Please input Note/Comment'))
        #         approval.write({
        #             'state': 'comment',
        #             'action_date': fields.Datetime.now(),
        #             'user_id': self.env.uid,
        #             'memo': note,
        #         })
        #         approval.update_fin_status()
        #     else:
        #         latest_approval = fin100.approver.sorted(lambda app: app.position_index)[-1]
        #         if self.env.user == latest_approval.mapped('employee_user_id') and not latest_approval.approve_active:
        #             latest_approval.write({
        #                 'action_date': fields.Datetime.now(),
        #                 'user_id': self.env.uid,
        #                 'memo': note,
        #             })
        # return True

    @api.multi
    def set_fin100_to_reject(self):
        print("FIN100.set_fin100_to_reject",self)
        for fin100 in self:
            fin100.check_reject = True
            fin100.has_history = True
            fin100.state = "reject"
        return True

    @api.multi
    def fin_set_to_draft(self):
        res = super(fw_pfb_FS100, self).fin_set_to_draft()
        if self.approver:
            self.approver.write({'user_id': ''})
            return res
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
        #         "FIN100 Set to Draft",
        #         str(self.write_date),
        #     ))
        # )
        log_message = message_log_stamp(self, "FIN100 Set to Draft", self.write_date)
        self.message_post(body=_(log_message))

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        print("FIN100.fields_view_get",self)
        env_fin = self.env['fw_pfb_fin_system_100']
        env_fin_approver = self.env['fw_pfb_fin_system_100_approver']
        params = self._context.get('params')
        checkRule = False
        if params :
            if "action" in params :
               if params["action"] == 1111 :
                   checkRule = True
        res = super(fw_pfb_FS100, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        if checkRule:
            fin100_domain = [
                ('state','not in',['draft','cancelled','reject', 'completed']),
            ]
            fin_list = env_fin.search(fin100_domain)
            to_hide_fin_list = env_fin.search([('id','not in',fin_list.ids)])
            if to_hide_fin_list:
                to_hide_fin_list.write({'show_fin': False})
            print("FOUND-FIN100 >>>>>", len(fin_list))
            for fin in fin_list:
                fin_user = []

                if fin.check_reject != True :
                    if fin.next_approval_user_ids:
                        fin_user += fin.next_approval_user_ids.ids
                    if fin.next_comment_user_ids:
                        fin_user += fin.next_comment_user_ids.ids

                if self._uid in fin_user:
                    if not fin.show_fin : # if show_fin is False
                        fin.show_fin = True
                else:
                    if fin.show_fin : # if show_fin is True
                        fin.show_fin = False
        return res

    @api.multi
    def check_missing_project(self):
        print("FIN100.check_missing_project", self)
        for fin100 in self:
            if fin100.fin_type in ['erob', 'proo']:
                lines_missing_project = fin100.fin_lines.filtered(lambda x: not x.projects_and_plan)
                if lines_missing_project:
                    raise UserError(_('Fin Lines missing project'))
        return True

    @api.multi
    def check_dummy_employee(self):
        print("FIN100.check_dummy_employee", self)
        for fin100 in self:
            for app in fin100.approver.filtered(lambda app: app.approve_active==True):
                if not app.employee_id.user_id:
                    raise UserError(_('Fin Approval, not allowed dummy employee'))

    @api.multi
    def fin_sent_to_supervisor(self):
        print("FIN100.fin_sent_to_supervisor", self)
        for fin100 in self:
            # fin100.fin_lines --> check missing project
            fin100.check_missing_project()
            # fin100.approver --> check dummy employee
            fin100.check_dummy_employee()
        return super(fw_pfb_FS100, self).fin_sent_to_supervisor()

    @api.multi
    def get_action_fin_100_to_approve(self):
        action = {
            'name': _('Pending Expenses'),
            'type': "ir.actions.act_window",
            'res_model': "fw_pfb_fin_system_100",
            'view_id': self.env.ref('fin_system.fin_system_100_pending_tree_view').id,
            'view_type': "form",
            'view_mode': "tree,form",
        }
        action['views'] = [
            (self.env.ref('fin_system.fin_system_100_pending_tree_view').id, 'tree'),
            (self.env.ref('fin_system.fin_system_100_request_form_view').id, 'form'),
        ]
        action['domain'] = """[
            ('state','not in',['draft', 'cancelled', 'reject', 'completed']),
            '|',
            ('next_approval_user_ids', 'in', %s),
            ('next_comment_user_ids', 'in', %s),
        ]""" %(self.env.user.ids, self.env.user.ids)
        return action

class fw_pfb_FS100Lines(models.Model):
    _inherit = 'fw_pfb_fin_system_100_line'
    _rec_name = "name"

    name = fields.Char(string="Name", compute="_compute_name", store=True)
    trigger = fields.Integer(string="trigger")
    balance = fields.Float(
        "FIN100 Line Balance",
        readonly=True,
        compute='_compute_fin100_line_balance',
        store=True
    )
    balance_percent = fields.Float("Balance in Percent", readonly=True, compute='_compute_fin100_line_balance', store=True)

    fin401_line_ids = fields.One2many('fw_pfb_fin_system_401_line', 'fin100_line_id', string="FIN401 LINE IDS")
    fin401_line_ids_ready = fields.One2many('fw_pfb_fin_system_401_line', 'fin100_line_id', string="FIN401 LINE IDS READY", compute='_get_fin401_datas')
    fin401_ids = fields.One2many('fw_pfb_fin_system_401', string="FIN401 IDS", compute='_get_fin401_datas')
    fin401_line_count = fields.Integer('FIN401 Line Count', compute='_get_fin401_datas', store=True)
    fin401_count = fields.Integer('FIN401 Count', compute='_get_fin401_datas', store=True)
    price_all_fin401 = fields.Float('FIN401 Amount', compute="_compute_fin100_line_balance", store=True)

    fin201_line_ids = fields.One2many('fw_pfb_fin_system_201_line', 'fin100_line_id', string="FIN201 LINE IDS")
    fin201_line_ids_ready = fields.One2many('fw_pfb_fin_system_201_line', 'fin100_line_id', string="FIN201 LINE IDS READY", compute='_get_fin201_datas')
    fin201_ids = fields.One2many('fw_pfb_fin_system_201', string="FIN201 IDS", compute='_get_fin201_datas')
    fin201_line_count = fields.Integer('FIN401 Line Count', compute='_get_fin201_datas', store=True)
    fin201_count = fields.Integer('FIN201 Count', compute='_get_fin201_datas', store=True)
    price_all_fin201 = fields.Float('FIN201 Amount', compute="_compute_fin100_line_balance", store=True)

    fin401_current_amount = fields.Float('FIN401 Current Amount', compute="_compute_fin100_line_balance", store=True)
    fin401_balance_amount = fields.Float('FIN401 Balance Amount', compute="_compute_fin100_line_balance", store=True)

    fin201_current_amount = fields.Float('FIN201 Current Amount', compute="_compute_fin100_line_balance", store=True)
    fin201_balance_amount = fields.Float('FIN201 Balance Amount', compute="_compute_fin100_line_balance", store=True)

    has_project = fields.Boolean('Has Project', compute='_compute_has_project')
    lock = fields.Boolean('MASTER LOCK', compute="_compute_lock")

    required_projects_and_plan = fields.Boolean(
        string='Required projects and plan',
        compute="_fin_type_projects_and_plan_required"
    )

    # Use for calculate Check Availability
    amount_before_change = fields.Float()

    @api.multi
    @api.depends('fin100_state', 'has_project')
    def _compute_lock(self):
        for fin100_line in self:
            #con1 = fin100_line.fin100_state not in ['draft', 'DirectorOfOffice']
            #con2 = fin100_line.has_project
            if fin100_line.fin100_state in ['cancelled','reject']:
                fin100_line.lock = True
            elif fin100_line.fin100_state not in ['draft', 'DirectorOfOffice'] and fin100_line.has_project:
                fin100_line.lock = True
            elif fin100_line.fin_id.fin_type == 'eroe' and not fin100_line.has_project and fin100_line.fin100_state == 'completed':
                fin100_line.lock = False
            elif fin100_line.fin_id.fin_type != 'eroe' and fin100_line.fin100_state == 'completed':
                fin100_line.lock = True
            else:
                fin100_line.lock = False
            print("FIN100_LINE._compute_lock", "---->", fin100_line.lock)
        return

    @api.multi
    @api.depends('projects_and_plan')
    def _compute_has_project(self):
        for fin100_line in self:
            print("FIN100_LINE._compute_has_project",self)
            has_project = True
            for line in self:
                line.has_project = line.projects_and_plan and True or False

    @api.depends('fin401_line_ids', 'fin401_line_ids.lend',
        #'fin401_line_ids.fin100_line_residual',
        #'fin401_line_ids.fin100_line_residual_amount',
        'fin401_line_ids.fin_id.state',
        'fin201_line_ids',
        'fin201_line_ids.payment_amount',
        'fin201_line_ids.fin_id.state',
        'trigger')
    def _compute_fin100_line_balance(self):
        print("FIN100_LINE._compute_fin100_line_balance",self)
        for fin100_line in self.filtered(lambda x: x.fin100_state not in ['cancelled', 'reject']):
            fin100_balance = fin100_balance_percent = 0.0
            fin401_expense = 0.0
            fin201_expense = 0.0
            records = []
            groups = {}

            for line in fin100_line.fin401_line_ids_ready.sorted(lambda x: x.fin_id.fin_date and x.fin_id.fin_no):
                key = line.fin_id.fin_date, line.fin_id.create_date, line.fin_id.fin_no, line.id
                groups.setdefault(key,False)
                groups[key] = line
            for line in fin100_line.fin201_line_ids_ready.sorted(lambda x: x.fin_id.fin_date and x.fin_id.fin_no):
                key = line.fin_id.fin_date, line.fin_id.create_date, line.fin_id.fin_no, line.id
                groups.setdefault(key,False)
                groups[key] = line
            if groups:
                fin100_line_balance = round(fin100_line.price_subtotal, 2) or 0.0
                fin100_401_balance = round(fin100_line_balance, 2)
                fin100_201_balance = round(fin100_line_balance, 2)
                # groups_sorted = collections.OrderedDict(sorted(groups.items()))
                groups_sorted = collections.OrderedDict(groups.items())
                

                for (fin_date, fin_create_date, fin_name, line_id), line in groups_sorted.items():

                    if line._name == 'fw_pfb_fin_system_401_line':
                        fin401_line = line
                        fin401_line.write({
                            'fin100_line_residual': fin100_line_balance,
                            #'fin100_line_residual_amount': fin100_line_balance - fin401_line.lend,
                            'fin100_line_residual_amount': fin100_401_balance - fin401_line.lend,
                            'fin401_current_amount': fin401_expense,
                            'fin201_current_amount': fin201_expense,
                        })
                        fin401_expense += line.lend or 0.0
                        fin100_401_balance -= fin401_line.lend
                        fin100_line_balance -= fin401_line.lend

                    elif line._name == 'fw_pfb_fin_system_201_line':
                        fin201_line = line
                        fin201_line.write({
                            'fin100_line_residual': round(fin100_line_balance, 2),
                            'fin100_line_residual_amount': round(fin100_201_balance, 2) - round(fin201_line.payment_amount, 2),
                            'fin401_current_amount': round(fin401_expense, 2),
                            'fin201_current_amount': round(fin201_expense, 2),
                        })
                        fin201_expense += round(fin201_line.payment_amount, 2) or 0.0
                        fin100_201_balance -= round(fin201_line.payment_amount, 2)
                        fin100_line_balance -= round(fin201_line.payment_amount, 2)


            #XXX
            #fin100_line_balance = fin100_line.price_subtotal - fin401_expense - fin201_expense
            fin100_line_balance = round(fin100_line.price_subtotal, 2) - round(fin201_expense, 2)

            fin100_401_balance = round(fin100_line.price_subtotal, 2) - round(fin401_expense, 2)
            fin100_201_balance = round(fin100_line.price_subtotal, 2) - round(fin201_expense, 2)
            fin100_balance_percent = round(fin100_line_balance, 2) * 100 / (round(fin100_line.price_subtotal, 2) or 1)

            fin100_line.update({
                'balance': fin100_line_balance,
                'balance_percent': fin100_balance_percent,
                'price_all_fin401': fin401_expense,
                'price_all_fin201': fin201_expense,
                'fin401_current_amount': fin401_expense,
                #'fin401_balance_amount': fin100_line_balance,
                'fin401_balance_amount': fin100_401_balance,
                'fin201_current_amount': fin201_expense,
                'fin201_balance_amount': fin100_201_balance,
            })

    def update_fin401_line_residual_amount(self):
        print("FIN100_LINE.update_fin401_line_residual_amount",self)
        for fin100_line in self.filtered(lambda x: x.fin100_state not in ['cancelled', 'reject']):
            tmp_balance = fin100_line.price_subtotal or 0.0
            for fin401_line in fin100_line.fin401_line_ids_ready:
                fin401_expense += fin401_line.lend or 0.0
                fin401_line.write({
                    'fin100_line_residual': tmp_balance,
                    'fin100_line_residual_amount': tmp_balance - fin401_line.lend,
                })
                tmp_balance -= fin401_line.lend
        return True

    @api.multi
    @api.depends('fin_id', 'product_id', 'trigger')
    def _compute_name(self):
        print("FIN100_LINE._compute_name",self)
        for fin100_line in self:
            fin100_line.name = fin100_line.name_get()[0][1]
            if fin100_line.fin_id.fin_type == 'erob' or fin100_line.fin_id.fin_type == 'proo':
                fin100_line.required_projects_and_plan = True

    def _fin_type_projects_and_plan_required(self):
        for fin100_line in self:
            if fin100_line.fin_id.fin_type == 'erob' or fin100_line.fin_id.fin_type == 'proo':
                fin100_line.required_projects_and_plan = True

    @api.multi
    @api.depends('fin401_line_ids')
    def _get_fin401_datas(self):
        print("FIN100_LINE._get_fin401_datas",self)
        for fin100_line in self:
            fin100_line.fin401_line_ids_ready = fin100_line.fin401_line_ids.filtered(lambda fin401_line: fin401_line.fin_id.state not in ['cancelled', 'reject'])
            fin100_line.fin401_ids = fin100_line.fin401_line_ids.mapped('fin_id')
            fin100_line.fin401_line_count = len(fin100_line.fin401_line_ids)
            fin100_line.fin401_count = len(fin100_line.fin401_ids)

    @api.multi
    @api.depends('fin201_line_ids')
    def _get_fin201_datas(self):
        print("FIN100_LINE._get_fin201_datas",self)
        for fin100_line in self:
            fin100_line.fin201_line_ids_ready = fin100_line.fin201_line_ids.filtered(lambda fin201_line: fin201_line.fin_id.state not in ['cancelled', 'reject'])
            fin100_line.fin201_ids = fin100_line.fin201_line_ids.mapped('fin_id')
            fin100_line.fin201_line_count = len(fin100_line.fin201_line_ids)
            fin100_line.fin201_count = len(fin100_line.fin201_ids)

    @api.multi
    def write(self, vals):
        print("FIN100_LINE.write", self, vals)
        res = super(fw_pfb_FS100Lines, self).write(vals)
        trigger_fields = ['fin_id', 'projects_and_plan', 'price_unit' ,'product_uom_qty', 'price_subtotal']
        trigger = False
        for trigger_field in trigger_fields:
            if trigger_field in vals:
                trigger = True
                break
        if trigger:
            self.mapped('fin_id').compute_line_project()
        return res

    @api.model
    def create(self, vals):
        print("FIN100_LINE.create", self, vals)
        res = super(fw_pfb_FS100Lines, self).create(vals)
        if res:
            res.fin_id.compute_line_project()
        return res

    @api.multi
    def name_get(self):
        print("FIN100_LINE.name_get",self)
        res = []
        for line in self:
            name = line.fin_id.display_name
            if line.product_id:
                name = "%s / %s"%(name, line.product_id.display_name)
            if line.id:
                name = "%s / *%s"%(name, line.id)
            res.append((line.id, name))
        return res

    @api.multi
    def button_trigger(self):
        print("FIN100_LINE.button_trigger",self)
        for obj in self:
            obj.trigger = randrange(1000001)
        return True

    @api.multi
    def action_view_fin401_line(self):
        print("FIN100_LINE.action_view_fin401_line",self)
        lines = self.mapped('fin401_line_ids')
        action = self.env.ref('fin_system_extension.action_fin_system_401_line').read()[0]
        action['context'] = {
            'default_fin100_line_id': self.id,
            'default_fin100_id': self.fin_id.id,
        }
        if lines:
            action['domain'] = [('id', 'in', lines.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.multi
    def action_view_fin201_line(self):
        print("FIN100_LINE.action_view_fin201_line",self)
        lines = self.mapped('fin201_line_ids')
        action = self.env.ref('fin_system_extension.action_fin_system_201_line').read()[0]
        action['context'] = {
            'default_fin100_line_id': self.id,
            'default_fin100_id': self.fin_id.id,
        }
        if lines:
            action['domain'] = [('id', 'in', lines.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    @api.constrains(
        'fin401_line_ids',
        'fin401_line_ids.lend',
        'fin401_line_ids.fin_id.state',
        'fin201_line_ids',
        'fin201_line_ids.payment_amount',
        'fin201_line_ids.fin_id.state',
        'balance')
    def _check_max_amount(self):
        print("FIN100_LINE._check_max_amount", self)
        for fin100_line in self:
            print("------------------------")
            print(fin100_line.balance)
            print("------------------------")
            if fin100_line.balance < 0.0:
                raise ValidationError(_('Budget is not enough for this request'))
        self._check_fin_balance_to_open_or_close()

    @api.multi
    def _check_fin_balance_to_open_or_close(self):
        for fin100_line in self:
            fin100_line_obj = self.env['fw_pfb_fin_system_100_line'].search([
                ('fin_id', '=', fin100_line.fin_id.id),
                ('projects_and_plan', '=', fin100_line.projects_and_plan.id)
            ])
            fin100_line_is_zero_count = len(fin100_line_obj.filtered(lambda r: r.balance == 0.0))
            if fin100_line_is_zero_count == len(fin100_line_obj):
                fin100_line.fin_id.is_fin_open = False
            else:
                fin100_line.fin_id.is_fin_open = True

        # print(len(self.filtered(lambda r: r.balance == 0.0)))
        # print(len(self))
        # for fin100_line in self:
        #     if not self.fin_id.is_fin_open:
        #         fin_return_balance = 0.0
        #         for fin_project in self.fin_id.fin_projects:
        #             fin_line_obj = self.env['fw_pfb_fin_system_100_line'].search([
        #                 ('fin_id', '=', self.fin_id.id),
        #                 ('projects_and_plan', '=', fin_project.projects_and_plan.id)
        #             ])
        #             for fin_line in fin_line_obj:
        #                 fin_return_balance += fin_line.balance
        #             fin_project.write({
        #                 'projects_return': fin_return_balance
        #             })
                    # projects_return = fin_return_balance


class fw_pfb_FS100Budget(models.Model):
    _inherit = 'fw_pfb_fin_system_100_projects'
    #Summary Fin lines grouping to each projects

    #for info
    #fin_id = fields.Many2one('fw_pfb_fin_system_100', required=True, ondelete='cascade', index=True, copy=False)
    #projects_and_plan = fields.Many2one('budget_system.projects_and_plan', readonly=True,)
    #projects_residual = fields.Float(string='Residual', related='projects_and_plan.historical_amount', readonly=True)
    #projects_reserve = fields.Float(string='Reserve', readonly=True)
    projects_residual_amount = fields.Float(string='Residual amount', compute='_compute_residual', store=True)

    projects_residual = fields.Float(string='Residual', related=False)
    projects_and_plan = fields.Many2one('account.analytic.account', index=True) # add index
    projects_return = fields.Float(
        string='Return',
    )
    fin100_state = fields.Selection(selection=ORIG_FIN100.STATE_SELECTION, string='FIN100 State', related="fin_id.state", index=True, store=True)
    fin100_date = fields.Date(related="fin_id.fin_date", index=True, store=True)



    @api.multi
    def get_current_project_balance(self):
        print("FIN100_PROJECT.get_current_project_balance",self)
        for obj in self:
            if not obj.projects_residual:
                obj.projects_residual = obj.projects_and_plan.budget_balance
        return True

    @api.depends('projects_reserve', 'projects_residual')
    def _compute_residual(self):
        print("FIN100_PROJECT._compute_residual",self)
        for line in self:
            if line.fin100_state not in ['cancelled', 'reject'] or not line.fin_id.is_fin_open:
                line['projects_residual_amount'] = line.projects_residual - line.projects_reserve + line.projects_return
            elif line.fin100_state in ['cancelled', 'reject']:
                line['projects_residual_amount'] = 0.0

class fw_pfb_FS100Approver(models.Model):
    _inherit = 'fw_pfb_fin_system_100_approver'

    approval_type = fields.Selection([
        #('optional', 'Approves, but the approval is optional'),
        ('mandatory', 'Is required to approve'),
        ('comment', 'Comments only'),
        ], 'Approval Type',
        default='mandatory', required=True)
    approve_step = fields.Integer(string='Step', default=0, required=True)
    trigger = fields.Integer(string="trigger")
    user_id = fields.Many2one('res.users', string="Approved by", copy=False)
    state = fields.Selection(selection_add=[('comment', 'Comment')])
    can_reset = fields.Boolean('Can Reset', compute='_compute_can_reset')

    def _compute_can_reset(self):
        print("FIN100_APPROVER._compute_can_reset",self)
        for approval in self:
            approval.can_reset = False
            last_approval = approval.fin_id.approver.filtered(lambda app: app.approval_type=='mandatory' and app.approve_active==True).sorted(lambda app: app.position_index)
            if last_approval:
                last_approval = last_approval[-1]
                if last_approval == approval and last_approval.state != 'pending':
                    if self.env.user.id in last_approval.employee_user_id.ids:
                        approval.can_reset = True
                    else:
                        approval.can_reset = False
            # force admin can reset for all
            if self.env.user.id == 2:
                approval.can_reset = True

    @api.multi
    @api.depends('employee_id','fin_position', 'approve_step')
    def name_get(self):
        print("FIN100_APPROVER.name_get",self)
        res = []
        for obj in self:
            name = obj.employee_id.display_name
            if obj.fin_position:
                fin_position = dict(obj._fields.get('fin_position').selection).get(obj.fin_position)
                name = "%s: %s"%(fin_position, name)
            if obj.approve_step:
                name = "Step %s. %s"%(obj.approve_step, name)
            res.append((obj.id, name))
        return res and res or super(fw_pfb_FS100Approver, self).name_get()

    @api.multi
    def update_fin_status(self):
        print("FIN100_APPROVER.update_fin_status",self)
        for approval_id in self:
            if approval_id.approve_position == 'DirectorOfDepartment':
                if approval_id.state == 'approve':
                    approval_id.fin_id.state = 'DirectorOfDepartment'
                    approval_id.fin_id.target_approver = 'RelatedGroup'
                elif approval_id.state == 'comment':
                    comment_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DirectorOfDepartment'),
                        ('approval_type', '=', 'comment'),
                        ('approve_active', '=', True)
                    ])
                    commented_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DirectorOfDepartment'),
                        ('approval_type', '=', 'comment'),
                        ('state', '=', 'comment'),
                    ])
                    comment_all = len(comment_approval_obj)
                    commented_count = len(commented_approval_obj)
                    if comment_all == commented_count:
                        approval_id.fin_id.state = 'DirectorOfDepartment'
                        approval_id.fin_id.target_approver = 'RelatedGroup'
            elif approval_id.approve_position == 'RelatedGroup':
                if approval_id.state == 'approve':
                    approval_id.fin_id.state = 'RelatedGroup'
                    approval_id.fin_id.target_approver = 'DirectorOfFinance'
                elif approval_id.state == 'comment':
                    comment_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'RelatedGroup'),
                        ('approval_type', '=', 'comment'),
                        ('approve_active', '=', True)
                    ])
                    commented_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'RelatedGroup'),
                        ('approval_type', '=', 'comment'),
                        ('state', '=', 'comment'),
                    ])
                    comment_all = len(comment_approval_obj)
                    commented_count = len(commented_approval_obj)
                    if comment_all == commented_count:
                        approval_id.fin_id.state = 'RelatedGroup'
                        approval_id.fin_id.target_approver = 'DirectorOfFinance'
            elif approval_id.approve_position == 'DirectorOfFinance':
                if approval_id.state == 'approve':
                    approval_id.fin_id.state = 'DirectorOfFinance'
                    approval_id.fin_id.target_approver = 'AssistantOfOffice'
                elif approval_id.state == 'comment':
                    comment_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DirectorOfFinance'),
                        ('approval_type', '=', 'comment'),
                        ('approve_active', '=', True)
                    ])
                    commented_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DirectorOfFinance'),
                        ('approval_type', '=', 'comment'),
                        ('state', '=', 'comment'),
                    ])
                    comment_all = len(comment_approval_obj)
                    commented_count = len(commented_approval_obj)
                    if comment_all == commented_count:
                        approval_id.fin_id.state = 'DirectorOfFinance'
                        approval_id.fin_id.target_approver = 'AssistantOfOffice'
            elif approval_id.approve_position == 'AssistantOfOffice':
                if approval_id.state == 'approve':
                    approval_id.fin_id.state = 'AssistantOfOffice'
                    approval_id.fin_id.target_approver = 'DeputyOfOffice'
                elif approval_id.state == 'comment':
                    comment_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'AssistantOfOffice'),
                        ('approval_type', '=', 'comment'),
                        ('approve_active', '=', True)
                    ])
                    commented_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'AssistantOfOffice'),
                        ('approval_type', '=', 'comment'),
                        ('state', '=', 'comment'),
                    ])
                    comment_all = len(comment_approval_obj)
                    commented_count = len(commented_approval_obj)
                    if comment_all == commented_count:
                        approval_id.fin_id.state = 'AssistantOfOffice'
                        approval_id.fin_id.target_approver = 'DeputyOfOffice'
            elif approval_id.approve_position == 'DeputyOfOffice':
                if approval_id.state == 'approve':
                    approval_id.fin_id.state = 'DeputyOfOffice'
                    approval_id.fin_id.target_approver = 'SmallNote'
                elif approval_id.state == 'comment':
                    comment_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DeputyOfOffice'),
                        ('approval_type', '=', 'comment'),
                        ('approve_active', '=', True)
                    ])
                    commented_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DeputyOfOffice'),
                        ('approval_type', '=', 'comment'),
                        ('state', '=', 'comment'),
                    ])
                    comment_all = len(comment_approval_obj)
                    commented_count = len(commented_approval_obj)
                    if comment_all == commented_count:
                        approval_id.fin_id.state = 'DeputyOfOffice'
                        approval_id.fin_id.target_approver = 'SmallNote'
            elif approval_id.approve_position == 'SmallNote':
                if approval_id.state == 'approve':
                    approval_id.fin_id.state = 'SmallNote'
                    approval_id.fin_id.target_approver = 'DirectorOfOffice'
                elif approval_id.state == 'comment':
                    comment_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'SmallNote'),
                        ('approval_type', '=', 'comment'),
                        ('approve_active', '=', True)
                    ])
                    commented_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'SmallNote'),
                        ('approval_type', '=', 'comment'),
                        ('state', '=', 'comment'),
                    ])
                    comment_all = len(comment_approval_obj)
                    commented_count = len(commented_approval_obj)
                    if comment_all == commented_count:
                        approval_id.fin_id.state = 'SmallNote'
                        approval_id.fin_id.target_approver = 'DirectorOfOffice'
            elif approval_id.approve_position == 'DirectorOfOffice':
                if approval_id.state == 'approve':
                    approval_id.fin_id.state = 'DirectorOfOffice'
                    approval_id.fin_id.target_approver = 'DirectorOfOffice'
                elif approval_id.state == 'comment':
                    comment_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DirectorOfOffice'),
                        ('approval_type', '=', 'comment'),
                        ('approve_active', '=', True)
                    ])
                    commented_approval_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                        ('fin_id', '=', approval_id.fin_id.id),
                        ('approve_position', '=', 'DirectorOfOffice'),
                        ('approval_type', '=', 'comment'),
                        ('state', '=', 'comment'),
                    ])
                    comment_all = len(comment_approval_obj)
                    commented_count = len(commented_approval_obj)
                    if comment_all == commented_count:
                        approval_id.fin_id.state = 'DirectorOfOffice'
                        approval_id.fin_id.target_approver = 'DirectorOfOffice'
        return True

    @api.multi
    def button_trigger(self):
        print("FIN100_APPROVER.button_trigger",self)
        for obj in self:
            obj.trigger = randrange(1000001)
        return True

    def check_actual_approver_list_for_reset(self, position_index=1, fin_id=None):
        approver_list = []
        # check step
        current_approver = self.env['fw_pfb_fin_system_100_approver'].search([
                ('fin_id', '=', fin_id),
                ('position_index', '=', position_index),
                ('approve_active', '=', True)
            ])
        fin100 = self.env['fw_pfb_fin_system_100'].search([
                ('id', '=', fin_id),
            ])
        if fin_id:
            approver_obj = self.env['fw_pfb_fin_system_100_approver'].search([
                    ('fin_id', '=', fin_id),
                    ('position_index', '>=', position_index),
                    ('approve_active', '=', True)
                ])
            # if in the same step - don't reset (don't add to the list)
            if approver_obj:
                for approver in approver_obj:
                    if current_approver.approval_type == 'comment':
                        step_list = [approver.approve_step for approver in fin100.approver.filtered(lambda l: l.approve_active)]
                        step_list = sorted(set(step_list))
                        # Get next step if there is no next step then last step (when next step = -1)
                        next_step = next(iter(filter(lambda l: l > current_approver.approve_step, step_list)), -1)
                        check_condition_step = []
                        if current_approver.approve_step not in check_condition_step:
                            check_condition_step.append(current_approver.approve_step)
                        if next_step != -1 and next_step not in check_condition_step:
                            check_condition_step.append(next_step)
                        if approver.approve_step not in check_condition_step or approver.position_index == position_index:
                            approver_list.append(approver)
                    else:
                        if approver.approve_step != current_approver.approve_step or approver.position_index == position_index or (approver.memo is None and approver.action_date is None):
                            approver_list.append(approver)
        return approver_list
            
    @api.multi
    def action_reset_approval(self):
        print("FIN100_APPROVER.button_reset_approval",self)
        approval_list = {}
        approval_list = self.check_actual_approver_list_for_reset(self.position_index, self.fin_id.id)
        try:
            self.fin_id.state = self.approve_position
        except:
            pass
        for approval in approval_list:
            fin100_obj = approval.fin_id
            approval.write({
                'memo': '',
                'action_date': False,
                'state': 'waiting',
                'user_id': False,
            })
            fin100_obj._add_pending_to_step_approver_fin(self.approve_step)
        # Log stamp
        action_name = ("RESET Approval on position : %s" % (str(self.position_index),))
        log_message = message_log_stamp(self, action_name, self.fin_id.write_date)
        self.fin_id.message_post(body=_(log_message))
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

class fw_pfb_FS100Approver_history(models.Model):
    _inherit = 'fw_pfb_fin_system_100_approver_history'

    approval_type = fields.Selection([
        #('optional', 'Approves, but the approval is optional'),
        ('mandatory', 'Is required to approve'),
        ('comment', 'Comments only'),
        ], 'Approval Type',
        default='mandatory', required=True)
    approve_step = fields.Integer(string='Step', default=0, required=True)
    trigger = fields.Integer(string="trigger")
    user_id = fields.Many2one('res.users', string="Approved by")
    state = fields.Selection(selection_add=[('comment', 'Comment')])

class WizardFIN100Approval(models.TransientModel):
    """
    This wizard will Approve/Reject/Comment for FIN100
    """
    _name = "wizard.fin100.approval"
    _description = "FIN100 Approval"

    def _default_next_approval(self):
        print("_default_next_approval",self)
        res = False
        if self._context.get('next_approval_id'):
            res = self.env['fw_pfb_fin_system_100_approver'].browse(self._context.get('next_approval_id'))
        return res

    def _default_next_comment(self):
        print("_default_next_comment",self)
        fin100_ids = self.env['fw_pfb_fin_system_100'].browse(self._context.get('active_ids'))
        next_comment_ids = fin100_ids.mapped('next_comment_ids').sorted(lambda x: x.id).ids
        return next_comment_ids

    def _default_next_comment_user(self):
        print("_default_next_comment_user",self)
        fin100_ids = self.env['fw_pfb_fin_system_100'].browse(self._context.get('active_ids'))
        next_comment_user_ids = fin100_ids.mapped('next_comment_ids').sorted(lambda x: x.id).mapped('employee_user_id')
        return next_comment_user_ids

    next_approval_id = fields.Many2one('fw_pfb_fin_system_100_approver', string='Next Approval', default=_default_next_approval)
    employee_user_id = fields.Many2one('res.users', string='Requested User', related="next_approval_id.employee_user_id")

    next_comment_ids = fields.Many2many('fw_pfb_fin_system_100_approver', string='Next Comment', default=_default_next_comment)
    next_comment_user_ids = fields.Many2many('res.users', string='Next Comment Users', default=_default_next_comment_user)

    approval_type = fields.Selection([
                ('mandatory', 'Is required to approve'),
                ('comment', 'Comments only')
            ], 
            string='Approval Type'
        )
    approval_step = fields.Integer(
                string="Approval step"
            )
    note = fields.Text(string="Memo", required=True)
    
    @api.multi
    def action_approve(self):
        print("WIZARD_FIN100_APPROVAL.action_approve",self)
        context = dict(self._context or {})
        active_id = context.get('active_id') or None
        fin100_obj = self.env['fw_pfb_fin_system_100'].browse(active_id)
        emp_obj = self.env['hr.employee'].search([
                ('user_id', '=', self._uid)
            ])
        if fin100_obj:
            fin100_obj.action_set_approve(
                        note=self.note,
                        employee_id=emp_obj.id,
                        step=self.approval_step
                    )
            return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_reject(self):
        print("WIZARD_FIN100_APPROVAL.action_reject",self)
        context = dict(self._context or {})
        active_id = context.get('active_id') or None
        fin100_obj = self.env['fw_pfb_fin_system_100'].browse(active_id)
        emp_obj = self.env['hr.employee'].search([
                ('user_id', '=', self._uid)
            ])
        if fin100_obj:
            fin100_obj.action_set_reject(
                        note=self.note,
                        employee_id=emp_obj.id,
                        step=self.approval_step
                    )
        # active_ids = context.get('active_ids', []) or []
        # fin100_ids = self.env['fw_pfb_fin_system_100'].browse(active_ids)
        # for fin100 in fin100_ids:
        #     fin100.action_set_reject(note=self.note)
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_comment(self):
        print("WIZARD_FIN100_APPROVAL.action_comment",self)
        context = dict(self._context or {})
        active_id = context.get('active_id') or None
        fin100_obj = self.env['fw_pfb_fin_system_100'].browse(active_id)
        emp_obj = self.env['hr.employee'].search([
                ('user_id', '=', self._uid)
            ])
        if fin100_obj:
            fin100_obj.action_set_comment(
                        note=self.note,
                        employee_id=emp_obj.id,
                        step=self.approval_step
                    )
        return {'type': 'ir.actions.act_window_close'}


class WizardFinRecomputeBudget(models.TransientModel):
    _name = 'wizard.fin.recompute.budget'

    @api.multi
    def action_recompute_budget(self):
        projects_and_plan = self.env['account.analytic.account'].search([], order='name')
        for pap in projects_and_plan:
            pap.button_force_compute_fin100_lines()
        return True

class WaitingFinSystem100Line(models.Model):
    _name = 'waiting.fin.system.100.line'

    fin_id = fields.Many2one(
                'fw_pfb_fin_system_100',
                string="FIN ID"
            )
    employee_id = fields.Many2one(
                'hr.employee',
                string="Employee name"
            )
    approval_type = fields.Selection([
                    ('mandatory', 'Is required to approve'),
                    ('comment', 'Comments only'),
                ], 
                string='Approval Type'
            )
    approval_step = fields.Integer(
                string='Approvel Step'
            )
