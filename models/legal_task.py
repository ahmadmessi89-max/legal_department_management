# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta

class LegalTask(models.Model):
    _name = 'legal.task'
    _description = 'إجراء / قضية / معاملة قانونية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'due_date asc, id desc'

    task_number = fields.Char(string="رقم المعاملة / القضية", copy=False, readonly=True, default=lambda self: _('مسودة'))
    name = fields.Char(string="عنوان الإجراء / المعاملة", required=True, tracking=True)
    legal_company_id = fields.Many2one(
        'legal.company',
        string="الشركة التابعة",
        required=True,
        ondelete='cascade',
        tracking=True
    )
    company_name = fields.Char(related='legal_company_id.name', string="اسم الشركة", store=True)
    
    ministry_id = fields.Many2one(
        'legal.ministry',
        string="الوزارة / الهيئة العامة",
        tracking=True,
        ondelete='restrict'
    )
    ministry_name = fields.Char(related='ministry_id.name', string="اسم الوزارة", store=True)

    department_id = fields.Many2one(
        'legal.department',
        string="الدائرة / القسم التابع",
        required=True,
        tracking=True,
        ondelete='restrict'
    )
    department_name = fields.Char(related='department_id.name', string="اسم الدائرة", store=True)

    @api.onchange('ministry_id')
    def _onchange_ministry_id(self):
        if self.ministry_id and self.department_id and self.department_id.ministry_id != self.ministry_id:
            self.department_id = False

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id and self.department_id.ministry_id and not self.ministry_id:
            self.ministry_id = self.department_id.ministry_id

    state = fields.Selection([
        ('draft', 'مسودة'),
        ('in_progress', 'قيد الإجراء'),
        ('pending_docs', 'بانتظار الوثائق وصحة الصدور'),
        ('done', 'منجز'),
        ('cancelled', 'ملغى')
    ], string="حالة الإجراء", default='draft', tracking=True)

    # Approvals & Permissions
    approval_state = fields.Selection([
        ('draft', 'مسودة'),
        ('to_approve', 'بانتظار موافقة المدير القانوني ⏳'),
        ('approved', 'تمت الموافقة والاعتماد ✓'),
        ('rejected', 'مرفوض من الإدارة ✕')
    ], string="حالة الموافقة القانونية", default='draft', tracking=True)

    approver_id = fields.Many2one('res.users', string="تم الاعتماد بواسطة", readonly=True, tracking=True)
    approval_date = fields.Datetime(string="تاريخ الاعتماد", readonly=True)

    # Multi-Lawyer Assignment for Case
    lawyer_id = fields.Many2one(
        'res.users',
        string="المحامي الرئيسي",
        default=lambda self: self.env.user,
        tracking=True
    )
    lawyer_ids = fields.Many2many(
        'res.users',
        'legal_task_lawyers_rel',
        'task_id',
        'user_id',
        string="المحامون المكلفون",
        default=lambda self: [self.env.user.id],
        tracking=True
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'legal_task_employees_rel',
        'task_id',
        'employee_id',
        string="فريق العمل (الموظفون)",
        tracking=True
    )

    session_date = fields.Date(string="تاريخ الجلسة", tracking=True)
    due_date = fields.Date(string="تاريخ الاستحقاق (DUE_DATE)", tracking=True)
    action_details = fields.Text(string="تفاصيل ومذكرات الإجراء والمطلوب")
    
    # Financial & Accounting Linkage
    expenses_amount = fields.Float(string="المصروفات والمبالغ المدفوعة (د.ع)", tracking=True)
    account_move_id = fields.Many2one('account.move', string="قيد / فاتورة المصروف في الحسابات", readonly=True, copy=False)
    account_payment_id = fields.Many2one('account.payment', string="سند الصرف المرتبط في الحسابات", readonly=True, copy=False)
    expense_account_id = fields.Many2one('account.account', string="حساب المصروف المحاسبي")
    
    is_urgent = fields.Boolean(string="عاجل ومستعجل ⚠️", default=False, tracking=True)
    is_overdue = fields.Boolean(string="متأخر", compute='_compute_overdue', store=False)

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'legal_task_ir_attachment_rel',
        'task_id',
        'attachment_id',
        string="مرفقات وكتب القضية"
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('task_number') or vals.get('task_number') in [_('مسودة'), 'مسودة', 'New', '/']:
                seq = self.env['ir.sequence'].next_by_code('legal.task')
                if seq:
                    vals['task_number'] = seq
                else:
                    today_str = fields.Date.today().strftime('%Y/%m')
                    vals['task_number'] = f"CASE/{today_str}/001"
        return super(LegalTask, self).create(vals_list)

    @api.depends('due_date', 'state')
    def _compute_overdue(self):
        today = date.today()
        for task in self:
            if task.due_date and task.due_date < today and task.state not in ['done', 'cancelled']:
                task.is_overdue = True
            else:
                task.is_overdue = False

    @api.model
    def _cron_check_upcoming_sessions(self):
        """Cron job to check upcoming court sessions and overdue tasks within 3 days and create activities / messages."""
        today = date.today()
        upcoming_date = today + timedelta(days=3)
        tasks = self.search([
            ('state', 'not in', ['done', 'cancelled']),
            '|',
            '&', ('session_date', '>=', today), ('session_date', '<=', upcoming_date),
            '&', ('due_date', '<', today), ('due_date', '!=', False)
        ])
        mail_activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for task in tasks:
            users_to_notify = task.lawyer_ids or (task.lawyer_id and [task.lawyer_id]) or [self.env.user]
            for user in users_to_notify:
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'legal.task'),
                    ('res_id', '=', task.id),
                    ('user_id', '=', user.id),
                    ('date_deadline', '>=', today)
                ], limit=1)
                if not existing:
                    is_court = bool(task.session_date and task.session_date <= upcoming_date)
                    summary = f"تنبيه جلسة قضائية قادمة: {task.name}" if is_court else f"تنبيه استحقاق متأخر: {task.name}"
                    task.activity_schedule(
                        activity_type_id=mail_activity_type.id if mail_activity_type else False,
                        date_deadline=task.session_date or task.due_date or today,
                        summary=summary,
                        note=f"يرجى متابعة الإجراءات والمستندات للقضية ({task.task_number}) العائدة لشركة {task.legal_company_id.name}.",
                        user_id=user.id
                    )

    def unlink(self):
        is_manager = self.env.user.has_group('legal_department_management.group_legal_manager') or self.env.user.has_group('base.group_system')
        if not is_manager:
            raise UserError("عذراً، صلاحية حذف المعاملات والقضايا محصورة بالمدير القانوني ومدير النظام (Administrator) فقط.")
        return super(LegalTask, self).unlink()

    def action_print_task_report(self):
        self.ensure_one()
        return self.env.ref('legal_department_management.action_report_legal_task').report_action(self)

    def action_request_approval(self):
        self.write({'approval_state': 'to_approve'})
        self.message_post(body="تم إرسال المعاملة إلى المدير القانوني لطلب الموافقة والاعتماد.")

    def action_approve(self):
        self.write({
            'approval_state': 'approved',
            'approver_id': self.env.user.id,
            'approval_date': datetime.now()
        })
        self.message_post(body=f"تمت الموافقة على المعاملة واعتمادها من قبل المدير القانوني ({self.env.user.name}).")

    def action_reject(self):
        self.write({
            'approval_state': 'rejected',
            'approver_id': self.env.user.id,
            'approval_date': datetime.now()
        })
        self.message_post(body=f"تم رفض المعاملة من قبل المدير القانوني ({self.env.user.name}).")

    def action_set_draft_approval(self):
        self.write({'approval_state': 'draft'})

    def action_set_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_set_pending_docs(self):
        self.write({'state': 'pending_docs'})

    def action_set_done(self):
        self.write({'state': 'done'})

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_set_cancelled(self):
        self.write({'state': 'cancelled'})
