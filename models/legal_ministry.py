# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LegalMinistry(models.Model):
    _name = 'legal.ministry'
    _description = 'الوزارة / الهيئة العامة'
    _order = 'sequence, name asc'

    name = fields.Char(string="اسم الوزارة / الهيئة العامة", required=True, index=True)
    code = fields.Char(string="رمز الوزارة / الاختصار")
    website = fields.Char(string="الموقع الإلكتروني الرسمي")
    phone = fields.Char(string="رقم الهاتف / الاستعلامات")
    address = fields.Text(string="المقر / العنوان")
    notes = fields.Text(string="ملاحظات وتفاصيل إضافية")
    sequence = fields.Integer(string="الترتيب", default=10)
    active = fields.Boolean(string="نشط", default=True)

    department_ids = fields.One2many(
        'legal.department',
        'ministry_id',
        string="الدوائر والجهات التابعة"
    )
    department_count = fields.Integer(string="عدد الدوائر التابعة", compute='_compute_department_count')
    task_count = fields.Integer(string="عدد المعاملات والقضايا", compute='_compute_task_count')

    @api.constrains('name')
    def _check_unique_name(self):
        for record in self:
            if not record.name:
                continue
            clean_name = record.name.strip()
            existing = self.search([
                ('id', '!=', record.id),
                ('name', '=ilike', clean_name)
            ], limit=1)
            if existing:
                raise ValidationError(_("اسم الوزارة / الهيئة العامة '%s' مسجل مسبقاً في النظام! لا يُسمح بإضافة وزارات مكررة.") % clean_name)

    @api.depends('department_ids')
    def _compute_department_count(self):
        for record in self:
            record.department_count = len(record.department_ids)

    def _compute_task_count(self):
        for record in self:
            record.task_count = self.env['legal.task'].search_count([
                ('department_id', 'in', record.department_ids.ids)
            ])

    def action_view_departments(self):
        self.ensure_one()
        return {
            'name': f'الدوائر التابعة لـ {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'legal.department',
            'view_mode': 'list,form',
            'domain': [('ministry_id', '=', self.id)],
            'context': {'default_ministry_id': self.id},
        }

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': f'قضايا ومعاملات {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'legal.task',
            'view_mode': 'list,form',
            'domain': [('department_id', 'in', self.department_ids.ids)],
            'context': {'default_ministry_id': self.id},
        }
