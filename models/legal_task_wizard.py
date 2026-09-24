# -*- coding: utf-8 -*-
from odoo import models, fields, api

class LegalTaskCreateWizard(models.TransientModel):
    _name = 'legal.task.create.wizard'
    _description = 'معالج بدء معاملة أو قضية جديدة'

    legal_company_id = fields.Many2one(
        'legal.company',
        string="الشركة / الموكل",
        required=True,
        help="اختر الشركة المعنية، أو أنشئ شركة جديدة مباشرة إذا لم تكن مسجلة مسبقاً."
    )
    ministry_id = fields.Many2one(
        'legal.ministry',
        string="الوزارة / الهيئة العامة",
        help="حدد الوزارة لتقليص وتصفية قائمة الدوائر التابعة لها."
    )
    department_id = fields.Many2one(
        'legal.department',
        string="الدائرة / الجهة الرسمية التابعة",
        help="اختر الدائرة أو المحكمة الرسمية المختصة بالإجراء."
    )

    @api.onchange('ministry_id')
    def _onchange_ministry_id(self):
        if self.ministry_id and self.department_id and self.department_id.ministry_id != self.ministry_id:
            self.department_id = False

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id and self.department_id.ministry_id and not self.ministry_id:
            self.ministry_id = self.department_id.ministry_id

    def action_proceed(self):
        self.ensure_one()
        context = {
            'default_legal_company_id': self.legal_company_id.id,
        }
        if self.ministry_id:
            context['default_ministry_id'] = self.ministry_id.id
        if self.department_id:
            context['default_department_id'] = self.department_id.id

        return {
            'name': f'إضافة إجراء / قضية جديدة ({self.legal_company_id.name})',
            'type': 'ir.actions.act_window',
            'res_model': 'legal.task',
            'view_mode': 'form',
            'target': 'current',
            'context': context
        }
