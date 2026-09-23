# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LegalDepartment(models.Model):
    _name = 'legal.department'
    _description = 'الجهة / الدائرة الرسمية'
    _order = 'sequence, name asc'

    name = fields.Char(string="اسم الدائرة / الجهة الرسمية", required=True, index=True)
    ministry_id = fields.Many2one(
        'legal.ministry',
        string="الوزارة / الهيئة العامة التابعة لها",
        ondelete='restrict',
        index=True
    )
    code = fields.Char(string="رمز الجهة / الاختصار")
    contact_person = fields.Char(string="الشخص المعني / الموظف المسؤول")
    phone = fields.Char(string="رقم الهاتف")
    address = fields.Text(string="العنوان / الموقع")
    notes = fields.Text(string="ملاحظات وتفاصيل إضافية")
    sequence = fields.Integer(string="الترتيب", default=10)
    active = fields.Boolean(string="نشط", default=True)

    task_count = fields.Integer(string="عدد المعاملات", compute='_compute_task_count')

    @api.constrains('name', 'ministry_id')
    def _check_unique_department(self):
        for record in self:
            if not record.name:
                continue
            clean_name = record.name.strip()
            domain = [
                ('id', '!=', record.id),
                ('name', '=ilike', clean_name)
            ]
            if record.ministry_id:
                domain.append(('ministry_id', '=', record.ministry_id.id))
            
            existing = self.search(domain, limit=1)
            if existing:
                if record.ministry_id:
                    raise ValidationError(_("الدائرة / الجهة الرسمية '%(dept)s' مسجلة مسبقاً لدى (%(min)s)! لا يمكن تكرار اسم الدائرة.") % {
                        'dept': clean_name,
                        'min': record.ministry_id.name
                    })
                else:
                    raise ValidationError(_("الدائرة / الجهة الرسمية '%s' مسجلة مسبقاً! لا يمكن تكرار اسم الدائرة.") % clean_name)

    def _compute_task_count(self):
        task_data = self.env['legal.task']._read_group(
            domain=[('department_id', 'in', self.ids)],
            groupby=['department_id'],
            aggregates=['__count']
        )
        counts = {dept.id: count for dept, count in task_data}
        for record in self:
            record.task_count = counts.get(record.id, 0)

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': f'معاملات {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'legal.task',
            'view_mode': 'list,form',
            'domain': [('department_id', '=', self.id)],
            'context': {
                'default_department_id': self.id,
                'default_ministry_id': self.ministry_id.id if self.ministry_id else False,
            },
        }
