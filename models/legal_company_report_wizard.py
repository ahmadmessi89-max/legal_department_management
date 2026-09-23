# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LegalCompanyReportWizard(models.TransientModel):
    _name = 'legal.company.report.wizard'
    _description = 'خيارات وفلترة تقرير ملف الشركة'

    company_id = fields.Many2one('legal.company', string="الشركة / الموكل", required=True)
    show_company_info = fields.Boolean(
        string="إظهار بطاقة معلومات وبيانات الشركة في التقرير",
        default=True,
        help="عند إلغاء التحديد سيتم إخفاء بيانات الشركة والتركيز فقط على جدول القضايا والمعاملات المفلترة"
    )
    
    filter_lawyer_id = fields.Many2one('res.users', string="فلترة حسب المحامي المكلف")
    filter_department_id = fields.Many2one('legal.department', string="فلترة حسب الدائرة / الجهة الرسمية")
    filter_state = fields.Selection([
        ('draft', 'مسودة'),
        ('in_progress', 'قيد الإجراء'),
        ('pending_docs', 'بانتظار الوثائق وصحة الصدور'),
        ('done', 'منجز'),
        ('cancelled', 'ملغى')
    ], string="فلترة حسب حالة الإجراء")
    
    filter_task_ids = fields.Many2many(
        'legal.task',
        'legal_report_wizard_task_rel',
        'wizard_id',
        'task_id',
        string="تحديد معاملات وقضايا معينة فقط",
        domain="[('legal_company_id', '=', company_id)]"
    )

    def action_print_report(self):
        self.ensure_one()
        tasks = self.company_id.task_ids

        # Apply Task Filters
        if self.filter_task_ids:
            tasks = self.filter_task_ids
        else:
            if self.filter_lawyer_id:
                tasks = tasks.filtered(lambda t: self.filter_lawyer_id.id in t.lawyer_ids.ids or t.lawyer_id.id == self.filter_lawyer_id.id)
            if self.filter_department_id:
                tasks = tasks.filtered(lambda t: t.department_id.id == self.filter_department_id.id)
            if self.filter_state:
                tasks = tasks.filtered(lambda t: t.state == self.filter_state)

        data = {
            'company_id': self.company_id.id,
            'show_company_info': self.show_company_info,
            'task_ids': tasks.ids,
            'filter_lawyer_name': self.filter_lawyer_id.name if self.filter_lawyer_id else False,
            'filter_department_name': self.filter_department_id.name if self.filter_department_id else False,
            'filter_state_label': dict(self._fields['filter_state'].selection).get(self.filter_state) if self.filter_state else False,
        }
        return self.env.ref('legal_department_management.action_report_legal_company').with_context(report_data=data).report_action(self.company_id)
