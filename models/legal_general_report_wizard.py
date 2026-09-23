# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date

class LegalGeneralReportWizard(models.TransientModel):
    _name = 'legal.general.report.wizard'
    _description = 'خيارات وفلترة تقرير الرقابة العامة الشامل للقضايا'

    company_ids = fields.Many2many(
        'legal.company',
        'legal_general_report_company_rel',
        'wizard_id',
        'company_id',
        string="الشركات والموكلين المشمولين",
        placeholder="اترك الحقل فارغاً لتضمين كافة الشركات، أو حدد شركات معينة..."
    )
    
    filter_lawyer_id = fields.Many2one('res.users', string="فلترة حسب المحامي المكلف", placeholder="كافة المحامين...")
    filter_ministry_id = fields.Many2one('legal.ministry', string="فلترة حسب الوزارة / الهيئة", placeholder="كافة الوزارات...")
    filter_department_id = fields.Many2one('legal.department', string="فلترة حسب الدائرة / الجهة الرسمية", placeholder="كافة الدوائر والجهات...")
    filter_state = fields.Selection([
        ('draft', 'مسودة'),
        ('in_progress', 'قيد الإجراء'),
        ('pending_docs', 'بانتظار الوثائق وصحة الصدور'),
        ('done', 'منجز'),
        ('cancelled', 'ملغى')
    ], string="فلترة حسب حالة الإجراء")

    date_from = fields.Date(string="من تاريخ استحقاق / جلسة")
    date_to = fields.Date(string="إلى تاريخ استحقاق / جلسة")
    
    group_by_company = fields.Boolean(string="تقسيم وتجميع التقرير حسب الشركة", default=True)

    filter_task_ids = fields.Many2many(
        'legal.task',
        'legal_gen_report_wizard_task_rel',
        'wizard_id',
        'task_id',
        string="تحديد قضايا ومعاملات معينة بالاسم (اختياري)",
        placeholder="اترك الحقل فارغاً لتضمين المعاملات تلقائياً حسب الفلاتر أعلاه..."
    )

    @api.onchange('filter_ministry_id')
    def _onchange_filter_ministry_id(self):
        if self.filter_ministry_id and self.filter_department_id and self.filter_department_id.ministry_id != self.filter_ministry_id:
            self.filter_department_id = False

    def action_print_general_report(self):
        self.ensure_one()
        
        domain = []
        if self.company_ids:
            domain.append(('legal_company_id', 'in', self.company_ids.ids))
        if self.filter_lawyer_id:
            domain.append('|')
            domain.append(('lawyer_ids', 'in', [self.filter_lawyer_id.id]))
            domain.append(('lawyer_id', '=', self.filter_lawyer_id.id))
        if self.filter_ministry_id:
            domain.append(('ministry_id', '=', self.filter_ministry_id.id))
        if self.filter_department_id:
            domain.append(('department_id', '=', self.filter_department_id.id))
        if self.filter_state:
            domain.append(('state', '=', self.filter_state))
        if self.date_from:
            domain.append('|')
            domain.append(('due_date', '>=', self.date_from))
            domain.append(('session_date', '>=', self.date_from))
        if self.date_to:
            domain.append('|')
            domain.append(('due_date', '<=', self.date_to))
            domain.append(('session_date', '<=', self.date_to))
        if self.filter_task_ids:
            domain.append(('id', 'in', self.filter_task_ids.ids))

        tasks = self.env['legal.task'].search(domain, order='legal_company_id, due_date asc')

        data = {
            'task_ids': tasks.ids,
            'company_names': ', '.join(self.company_ids.mapped('name')) if self.company_ids else 'كافة الشركات والكيانات',
            'filter_lawyer_name': self.filter_lawyer_id.name if self.filter_lawyer_id else 'كافة المحامين',
            'filter_department_name': self.filter_department_id.name if self.filter_department_id else 'كافة الدوائر الرسمية',
            'filter_state_label': dict(self._fields['filter_state'].selection).get(self.filter_state) if self.filter_state else 'كافة الحالات',
            'date_from': str(self.date_from) if self.date_from else False,
            'date_to': str(self.date_to) if self.date_to else False,
            'group_by_company': self.group_by_company,
        }
        
        # Use active company or first company or current user company as dummy doc
        dummy_record = self.company_ids[0] if self.company_ids else self.env['legal.company'].search([], limit=1)
        if not dummy_record:
            dummy_record = self.env.user.company_id

        return self.env.ref('legal_department_management.action_report_legal_general_overview').with_context(report_data=data).report_action(dummy_record)
