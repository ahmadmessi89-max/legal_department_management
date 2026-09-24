# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class LegalCompany(models.Model):
    _name = 'legal.company'
    _description = 'شركة / مؤسسة قانونية موكلة'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(string="اسم الشركة / الموكل", required=True, index=True, tracking=True)
    code = fields.Char(string="رمز الشركة / المرجع", copy=False, tracking=True)
    company_type = fields.Selection([
        ('llc', 'شركة ذات مسؤولية محدودة (LLC)'),
        ('joint_stock', 'شركة مساهمة خاصة'),
        ('sole', 'مشروع فردي / شخصي'),
        ('foreign_branch', 'فرع شركة أجنبية'),
        ('partnership', 'شركة تضامنية')
    ], string="نوع الكيان القانوني", default='llc', tracking=True)
    
    owner_name = fields.Char(string="المدير المفوض / المالك الرئيسي", tracking=True)
    entity_type = fields.Char(string="طبيعة النشاط التجاري", tracking=True)
    registration_number = fields.Char(string="رقم هويّة تسجيل الشركات", tracking=True)
    tax_number = fields.Char(string="الرقم الضريبي الرسمي", tracking=True)
    phone = fields.Char(string="هاتف الاتصال", tracking=True)
    email = fields.Char(string="البريد الإلكتروني المعتمد", tracking=True)
    address = fields.Text(string="العنوان والمقر القانوني", tracking=True)
    notes = fields.Text(string="ملاحظات وتفاصيل التأسيس")
    active = fields.Boolean(default=True, string="نشط")

    # Multi-Lawyer Assignment
    lawyer_id = fields.Many2one(
        'res.users',
        string="المحامي الرئيسي",
        default=lambda self: self.env.user,
        tracking=True
    )
    lawyer_ids = fields.Many2many(
        'res.users',
        'legal_company_lawyers_rel',
        'company_id',
        'user_id',
        string="المحامون المكلفون بالشركة",
        default=lambda self: [self.env.user.id],
        tracking=True
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'legal_company_employees_rel',
        'company_id',
        'employee_id',
        string="فريق العمل (دليل الموظفين)",
        tracking=True
    )

    # Attachments & Documents
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'legal_company_ir_attachment_rel',
        'company_id',
        'attachment_id',
        string="مستندات ووثائق الشركة"
    )
    document_count = fields.Integer(string="عدد المستندات", compute='_compute_document_count')

    task_ids = fields.One2many('legal.task', 'legal_company_id', string="الإجراءات القانونية")
    task_count = fields.Integer(string="عدد الإجراءات", compute='_compute_task_stats', store=True)
    department_count = fields.Integer(string="عدد الدوائر المعنية", compute='_compute_task_stats', store=True)
    ministry_count = fields.Integer(string="عدد الوزارات المعنية", compute='_compute_task_stats', store=True)
    total_expenses = fields.Float(string="إجمالي المصروفات (د.ع / $)", compute='_compute_task_stats', store=True)
    pending_tasks_count = fields.Integer(string="الإجراءات القائمة", compute='_compute_task_stats', store=True)
    
    department_cards_html = fields.Html(string="نوافذ الوزارات والدوائر الرسمية", compute='_compute_department_cards_html')

    @api.depends('attachment_ids')
    def _compute_document_count(self):
        for rec in self:
            rec.document_count = len(rec.attachment_ids)

    @api.depends('task_ids', 'task_ids.expenses_amount', 'task_ids.state', 'task_ids.department_id', 'task_ids.ministry_id')
    def _compute_task_stats(self):
        for company in self:
            company.task_count = len(company.task_ids)
            depts = company.task_ids.mapped('department_id')
            company.department_count = len(depts)
            ministries = company.task_ids.mapped('ministry_id')
            company.ministry_count = len(ministries)
            company.total_expenses = sum(company.task_ids.mapped('expenses_amount'))
            company.pending_tasks_count = len(company.task_ids.filtered(
                lambda t: t.state in ['draft', 'in_progress', 'pending_docs']
            ))

    def _compute_department_cards_html(self):
        state_labels = {
            'draft': ('مسودة', '#eff6ff', '#1d4ed8', '#bfdbfe'),
            'in_progress': ('قيد الإجراء', '#eff6ff', '#2563eb', '#bfdbfe'),
            'pending_docs': ('طلب وثائق', '#fffbeb', '#b45309', '#fde68a'),
            'done': ('منجز ✓', '#f0fdf4', '#15803d', '#bbf7d0'),
            'cancelled': ('ملغي', '#fef2f2', '#b91c1c', '#fecaca')
        }

        for company in self:
            tasks = company.task_ids
            min_dict = {}

            for t in tasks:
                dept = t.department_id
                ministry = t.ministry_id or (dept.ministry_id if dept else False)
                min_id = ministry.id if ministry else 0
                min_name = ministry.name if ministry else "جهات وهيئات حكومية عامة"

                if min_id not in min_dict:
                    min_dict[min_id] = {
                        'ministry': ministry,
                        'min_name': min_name,
                        'depts': {},
                        'total_count': 0,
                        'pending_count': 0,
                        'done_count': 0,
                        'lawyers': set(),
                    }
                min_dict[min_id]['total_count'] += 1
                if t.state in ['draft', 'in_progress', 'pending_docs']:
                    min_dict[min_id]['pending_count'] += 1
                elif t.state == 'done':
                    min_dict[min_id]['done_count'] += 1
                for l in t.lawyer_ids:
                    min_dict[min_id]['lawyers'].add(l.name)

                dept_id = dept.id if dept else 0
                dept_name = dept.name if dept else "معاملات عامة"
                if dept_id not in min_dict[min_id]['depts']:
                    min_dict[min_id]['depts'][dept_id] = {
                        'dept': dept,
                        'dept_name': dept_name,
                        'tasks': [],
                        'pending_count': 0,
                        'done_count': 0,
                    }
                min_dict[min_id]['depts'][dept_id]['tasks'].append(t)
                if t.state in ['draft', 'in_progress', 'pending_docs']:
                    min_dict[min_id]['depts'][dept_id]['pending_count'] += 1
                elif t.state == 'done':
                    min_dict[min_id]['depts'][dept_id]['done_count'] += 1

            cards_html = []
            cards_html.append('<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 20px; padding: 10px 0;">')

            for min_id, m_data in min_dict.items():
                min_name = m_data['min_name']
                depts_count = len(m_data['depts'])
                
                if m_data["pending_count"] > 0:
                    status_badge = f'<span class="badge px-2 py-1" style="background-color: #fffbeb !important; color: #b45309 !important; border: 1px solid #fde68a !important; font-weight: 800; font-size: 0.8rem;"><i class="fa fa-clock-o me-1"></i>{m_data["pending_count"]} جارية</span>'
                else:
                    status_badge = f'<span class="badge px-2 py-1" style="background-color: #f0fdf4 !important; color: #15803d !important; border: 1px solid #bbf7d0 !important; font-weight: 800; font-size: 0.8rem;"><i class="fa fa-check me-1"></i>{m_data["done_count"]} منجزة</span>'

                lawyers_str = ", ".join(list(m_data['lawyers'])[:2]) if m_data['lawyers'] else "المحامي المسؤول"

                # Build collapsible accordion for each department under this ministry
                depts_html_list = []
                for dept_id, d_data in m_data['depts'].items():
                    d_name = d_data['dept_name']
                    d_tasks = d_data['tasks']
                    
                    tasks_items = []
                    for t in d_tasks:
                        s_name, s_bg, s_col, s_border = state_labels.get(t.state, (t.state, '#f1f5f9', '#475569', '#cbd5e1'))
                        urgent_tag = '<span class="badge px-1 py-0 me-1" style="background-color: #fff1f2; color: #e11d48; border: 1px solid #fecdd3; font-size: 0.7rem;">⚠️ عاجل</span>' if t.is_urgent else ''
                        
                        item = f"""
                        <a href="/odoo/action-legal_department_management.action_legal_task/{t.id}" 
                           onclick="if(window.odoo &amp;&amp; window.odoo.__WOWL_DEBUG__ &amp;&amp; window.odoo.__WOWL_DEBUG__.root){{ window.odoo.__WOWL_DEBUG__.root.env.services.action.doAction({{type:'ir.actions.act_window',res_model:'legal.task',res_id:{t.id},views:[[false,'form']],target:'current'}}); return false; }}"
                           class="d-flex justify-content-between align-items-center p-2 rounded text-decoration-none shadow-sm" 
                           style="background-color: #ffffff; border: 1px solid #e2e8f0; margin-bottom: 5px; cursor: pointer; transition: all 0.2s;"
                           onmouseover="this.style.borderColor='#714b67'; this.style.backgroundColor='#faf5f9';"
                           onmouseout="this.style.borderColor='#e2e8f0'; this.style.backgroundColor='#ffffff';">
                            <div style="text-align: right; overflow: hidden; text-overflow: ellipsis;">
                                <div style="color: #0f172a; font-weight: 700; font-size: 0.88rem;">
                                    <i class="fa fa-file-text-o text-primary me-1"></i>{t.name}
                                </div>
                                <div class="d-flex align-items-center gap-2 mt-1" style="font-size: 0.75rem; color: #64748b;">
                                    <span class="badge font-monospace px-1 py-0" style="background-color: #f1f5f9; color: #1e293b; border: 1px solid #cbd5e1;">🏷️ {t.task_number}</span>
                                    {urgent_tag}
                                    {f'<span><i class="fa fa-calendar me-1"></i>{t.session_date}</span>' if t.session_date else ''}
                                </div>
                            </div>
                            <div class="ms-2">
                                <span class="badge px-2 py-1" style="background-color: {s_bg} !important; color: {s_col} !important; border: 1px solid {s_border} !important; font-weight: 700; font-size: 0.72rem;">
                                    {s_name}
                                </span>
                            </div>
                        </a>
                        """
                        tasks_items.append(item)

                    tasks_html = "".join(tasks_items)

                    dept_accordion = f"""
                    <details open="open" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 7px 10px; margin-bottom: 8px;">
                        <summary style="font-weight: 700; color: #1e293b; font-size: 0.88rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center; outline: none; user-select: none;">
                            <span><i class="fa fa-university text-primary me-2"></i>{d_name} <span class="text-muted fw-normal" style="font-size: 0.78rem;">({len(d_tasks)} معاملات)</span></span>
                            <span class="badge" style="background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; font-size: 0.7rem;">▼ طي / فتح</span>
                        </summary>
                        <div style="margin-top: 8px;">
                            {tasks_html}
                        </div>
                    </details>
                    """
                    depts_html_list.append(dept_accordion)

                all_depts_html = "".join(depts_html_list)

                card = f"""
                <div class="o_legal_company_box p-3 rounded-3 shadow-sm" style="background-color: #ffffff !important; background: #ffffff !important; color: #0f172a !important; border: 1px solid #e2e8f0 !important; border-right: 5px solid #714b67 !important;">
                    <!-- Ministry Header -->
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span class="badge px-2 py-1" style="background-color: #f3f0f3 !important; color: #714b67 !important; border: 1px solid #d4c5d2 !important; font-weight: 800; font-size: 0.82rem;">
                            🏛️ {min_name}
                        </span>
                        {status_badge}
                    </div>

                    <!-- Ministry Title -->
                    <div class="mb-3" style="color: #0f172a !important; font-weight: 800; font-size: 1.15rem; line-height: 1.4;">
                        <i class="fa fa-building-o text-primary me-2"></i>
                        <span>{min_name}</span>
                    </div>

                    <!-- Dropdowns of Departments and their Tasks -->
                    <div style="margin-bottom: 12px;">
                        {all_depts_html}
                    </div>

                    <!-- Card Footer -->
                    <div class="d-flex justify-content-between align-items-center pt-2 mt-2" style="border-top: 1px solid #e2e8f0 !important;">
                        <div class="d-flex gap-2">
                            <span class="badge px-2 py-1" style="background-color: #f8fafc !important; color: #0f172a !important; border: 1px solid #cbd5e1 !important; font-weight: 700; font-size: 0.78rem;">
                                <i class="fa fa-gavel text-primary me-1"></i>{m_data["total_count"]} قضايا
                            </span>
                            <span class="badge px-2 py-1" style="background-color: #f1f5f9 !important; color: #334155 !important; border: 1px solid #cbd5e1 !important; font-weight: 700; font-size: 0.78rem;">
                                <i class="fa fa-university text-secondary me-1"></i>{depts_count} دوائر تابعة
                            </span>
                        </div>
                        <div class="small text-muted" style="font-size: 0.78rem;">
                            <i class="fa fa-user me-1 text-secondary"></i>{lawyers_str}
                        </div>
                    </div>
                </div>
                """
                cards_html.append(card)

            if not min_dict:
                cards_html.append("""
                <div class="p-4 text-center rounded-3" style="background-color: #ffffff; border: 2px dashed #cbd5e1; grid-column: 1 / -1;">
                    <i class="fa fa-folder-open-o fa-3x text-muted mb-2"></i>
                    <h5 class="text-secondary fw-bold">لا توجد معاملات مسجلة لهذه الشركة لدى أي وزارة حتى الآن</h5>
                    <p class="text-muted small">يمكنك البدء بالضغط على زر <strong>(➕ بدء معاملة جديدة لهذه الشركة)</strong> أعلاه لاختيار الوزارة والجهة الرسمية وبدء الإجراء فوراً.</p>
                </div>
                """)

            cards_html.append('</div>')
            company.department_cards_html = "".join(cards_html)

    def unlink(self):
        is_manager = self.env.user.has_group('legal_department_management.group_legal_manager') or self.env.user.has_group('base.group_system')
        if not is_manager:
            raise UserError("عذراً، صلاحية حذف الشركات والموكلين محصورة بالمدير القانوني ومدير النظام فقط.")
        return super(LegalCompany, self).unlink()

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'name': f'معاملات {self.name} حسب الوزارات والدوائر الرسمية',
            'type': 'ir.actions.act_window',
            'res_model': 'legal.task',
            'view_mode': 'kanban,list,form,calendar',
            'domain': [('legal_company_id', '=', self.id)],
            'context': {
                'default_legal_company_id': self.id,
                'search_default_group_ministry': 1,
                'search_default_group_dept': 1,
            },
        }

    def action_create_new_task(self):
        self.ensure_one()
        return {
            'name': f'إضافة إجراء / قضية جديدة - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'legal.task.create.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_legal_company_id': self.id,
            },
        }

    def action_print_company_report(self):
        self.ensure_one()
        return {
            'name': f'خيارات وفلترة طباعة التقرير - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'legal.company.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_company_id': self.id,
                'default_show_company_info': True,
            }
        }
