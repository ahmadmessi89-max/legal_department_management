# Demo data for the money stream's screens (law-office preset).
#
# Run in `odoo-bin shell -c <conf> -d ldm_m < docs/ldm/tools/seed_money.py` on a
# database with the module installed and nothing else seeded. It creates one
# user per role (login = password, Arabic, Asia/Baghdad), Iraqi clients, fee
# agreements, client money, a runner's advance, time, an invoice with a partial
# payment and a conflict waiting for a partner, then writes the capture lists
# docs/ldm/evidence/03-money/screens-<role>.json with the real record ids.
import datetime as dt
import json
import os

from dateutil.relativedelta import relativedelta

M = "legal_department_management"
today = dt.date.today()
OUT = os.path.join(os.getcwd(), "docs", "ldm", "evidence", "03-money")
os.makedirs(OUT, exist_ok=True)

company = env.company
company.write({"name": "مكتب بغداد للمحاماة والاستشارات القانونية", "ldm_calendar_id": env.ref(f"{M}.ldm_calendar_iraq").id})
Settings = env["res.config.settings"]
Settings._ldm_apply_preset("office")
employee = env.ref("base.group_user")
employee._apply_group(env.ref(f"{M}.group_ldm_time"))
if Settings.create({}).ldm_iqd_can_round:
    Settings.create({}).action_ldm_iqd_whole_dinars()
iqd = company.currency_id
usd = env.ref("base.USD")
usd.active = True
if not usd.rate_ids:
    env["res.currency.rate"].create({"name": "2026-01-01", "currency_id": usd.id, "rate": 1 / 1310.0,
                                     "company_id": company.id})

# Arabic for this stream's data records (the integrator puts these in ar.po).
AR = {
    f"{M}.ldm_expense_category_court_fee": "رسم الدعوى",
    f"{M}.ldm_expense_category_pension_stamp": "طابع صندوق التقاعد",
    f"{M}.ldm_expense_category_expert_deposit": "أمانة أجور الخبير",
    f"{M}.ldm_expense_category_publication": "النشر في الصحف",
    f"{M}.ldm_expense_category_notary_fee": "رسم كاتب العدل",
    f"{M}.ldm_expense_category_execution_fee": "رسم التنفيذ",
    f"{M}.ldm_expense_category_government_fee": "رسم حكومي",
    f"{M}.ldm_expense_category_transport": "نقل",
    f"{M}.ldm_expense_category_other": "أخرى",
}
for xmlid, name in AR.items():
    env.ref(xmlid).with_context(lang="ar_001").name = name
MESSAGES = {
    "ldm_message_hearing_result": ("نتيجة الجلسة", "نتيجة جلسة اليوم",
        "السيد/السيدة {client} المحترم،\nانتهت جلسة {date} في {matter} ({matter_number}) أمام {court} إلى: {outcome}.\n"
        "موعد الجلسة القادمة {next_date}. {needed}\n{responsible}، {office}"),
    "ldm_message_hearing_reminder": ("تذكير بالجلسة", "تذكير بموعد جلستكم",
        "السيد/السيدة {client} المحترم،\nنذكّركم بأن الجلسة القادمة في {matter} ({matter_number}) يوم {next_date} أمام {court}. {needed}\n{office}"),
    "ldm_message_missing_documents": ("مستمسكات ناقصة", "مستمسكات ما زلنا نحتاجها",
        "السيد/السيدة {client} المحترم،\nلإكمال {matter} ({matter_number}) ما زلنا نحتاج: {documents}.\nيرجى إرسالها بأقرب وقت.\n{responsible}، {office}"),
    "ldm_message_instalment_due": ("دفعة مستحقة", "دفعة أتعاب مستحقة",
        "السيد/السيدة {client} المحترم،\nبموجب عقد الأتعاب، تستحق الدفعة «{fee}» بمبلغ {amount} بتاريخ {due_date}.\nمع الشكر.\n{office}"),
    "ldm_message_statement_ready": ("كشف الحساب جاهز", "كشف حسابكم",
        "السيد/السيدة {client} المحترم،\nكشف حسابكم لغاية {today} جاهز، والرصيد المستحق {balance}.\nيمكننا إرسال نسخة عند الطلب.\n{office}"),
}
for xmlid, (name, subject, body) in MESSAGES.items():
    env.ref(f"{M}.{xmlid}").with_context(lang="ar_001").write({"name": name, "subject": subject, "body": body})


def user(login, name, *groups):
    found = env["res.users"].search([("login", "=", login)])
    if found:
        return found
    return env["res.users"].with_context(no_reset_password=True).create({
        "name": name, "login": login, "password": login, "lang": "ar_001", "tz": "Asia/Baghdad",
        "group_ids": [(6, 0, [env.ref("base.group_user").id] + [env.ref(g).id for g in groups])],
    })


lawyer = user("money_lawyer", "سارة كريم العبيدي", f"{M}.group_legal_user")
lawyer2 = user("money_lawyer2", "علي حسن الجبوري", f"{M}.group_legal_user")
clerk = user("money_clerk", "مصطفى عادل (معقّب)", f"{M}.group_ldm_clerk")
billing = user("money_billing", "زينب فاضل (المحاسبة)", f"{M}.group_ldm_billing_user")
manager = user("money_manager", "المحامي حيدر الموسوي (الشريك)", f"{M}.group_legal_manager")
env.ref("base.user_admin").write({"lang": "ar_001", "tz": "Asia/Baghdad"})
if "odoobot_state" in env["res.users"]._fields:
    # OdooBot's first-login chat fills a phone screen; the demo users do not need it.
    (lawyer | lawyer2 | clerk | billing | manager).write({"odoobot_state": "disabled"})

Ministry, Department = env["legal.ministry"], env["legal.department"]
council = Ministry.create({"name": "مجلس القضاء الأعلى", "body_kind": "judicial"})
karkh = Department.create({"name": "محكمة بداءة الكرخ", "ministry_id": council.id, "body_kind": "court",
                           "court_degree": "first_instance"})
rusafa = Department.create({"name": "محكمة بداءة الرصافة", "ministry_id": council.id, "body_kind": "court",
                            "court_degree": "first_instance"})
execution = Department.create({"name": "مديرية تنفيذ الكرخ", "ministry_id": council.id, "body_kind": "execution",
                               "court_degree": "execution"})

Company = env["legal.company"]
rafidain = Company.create({"name": "شركة الرافدين للمقاولات العامة", "phone": "0770 123 4567", "lawyer_id": lawyer.id,
                           "lawyer_ids": [(6, 0, [lawyer.id, clerk.id])], "registration_number": "م.ش/4471",
                           "company_type": "llc"})
gulf = Company.create({"name": "فرع شركة الخليج للاستشارات الهندسية", "phone": "+964 780 222 3344",
                       "lawyer_id": lawyer.id, "lawyer_ids": [(6, 0, [lawyer.id])], "company_type": "foreign_branch"})
ahmed = Company.create({"name": "أحمد جاسم محمد", "client_kind": "individual", "phone": "07901112233",
                        "lawyer_id": lawyer.id, "lawyer_ids": [(6, 0, [lawyer.id])]})
dijla = Company.create({"name": "شركة دجلة للتجارة العامة", "phone": "07811230000", "lawyer_id": lawyer2.id,
                        "lawyer_ids": [(6, 0, [lawyer2.id])]})
for client in (rafidain, gulf, ahmed, dijla):
    client.partner_id.write({"lang": "ar_001"})

Task = env["legal.task"]
suit = env.ref(f"{M}.ldm_template_civil_lawsuit")
commercial = env.ref(f"{M}.ldm_template_commercial_lawsuit")
exec_t = env.ref(f"{M}.ldm_template_execution")
consult = env.ref(f"{M}.ldm_template_consultation")


def matter(client, template, name, department, value, currency=None, opponent=None, key_date=None, user=None):
    vals = {"template_id": template.id, "legal_company_id": client.id, "name": name,
            "department_id": department.id if department else False, "our_role": "plaintiff"}
    if opponent:
        vals["opponent_name"] = opponent
    if key_date:
        vals["key_date"] = str(key_date)
    task = Task.browse(Task.with_user(user or client.lawyer_id).create_from_template(vals))
    task.write({"matter_value": value, "currency_id": (currency or iqd).id, "law_branch": template.law_branch or "civil"})
    return task


m_contract = matter(rafidain, suit, "مطالبة بمستحقات عقد مقاولة مجمع سكني", karkh, 150_000_000,
                    opponent="شركة البناء الحديث", key_date=today + dt.timedelta(days=6))
m_debt = matter(rafidain, commercial, "دعوى دين تجاري على مصرف الشمال التجاري", rusafa, 45_000_000,
                opponent="مصرف الشمال التجاري", key_date=today + dt.timedelta(days=13))
m_ahmed = matter(ahmed, suit, "دعوى تعويض عن حادث مروري", karkh, 20_000_000,
                 opponent="شركة النقل السريع", key_date=today + dt.timedelta(days=9))
m_gulf = matter(gulf, consult, "استشارة في عقد توريد معدات", None, 0)
m_exec = matter(rafidain, exec_t, "تنفيذ حكم على شركة الإعمار الأولى", execution, 30_000_000,
                opponent="شركة الإعمار الأولى")
m_dijla = matter(dijla, commercial, "مطالبة تجارية بقيمة شحنة", rusafa, 85_000, currency=usd,
                 opponent="شركة الأفق للاستيراد", user=lawyer2)

# Fee agreements -----------------------------------------------------------
Engagement = env["legal.engagement"]
eng_rafidain = Engagement.create({
    "legal_company_id": rafidain.id, "lawyer_id": lawyer.id, "fee_type": "installments", "amount": 12_000_000,
    "success_percent": 5, "currency_id": iqd.id, "date_start": today - relativedelta(months=2), "signed": True,
    "note": "تمثيل الشركة في دعوى المطالبة بمستحقات عقد المقاولة بجميع مراحلها، ودعوى الدين التجاري، "
            "ومتابعة التنفيذ. لا تشمل الأتعاب أي دعوى جديدة تقام لاحقاً.",
    "line_ids": [
        (0, 0, {"name": "الدفعة الأولى عند التوقيع", "trigger_event": "signing", "amount": 4_000_000, "sequence": 1}),
        (0, 0, {"name": "الدفعة الثانية عند إقامة الدعوى", "trigger_event": "filing", "amount": 3_000_000, "sequence": 2}),
        (0, 0, {"name": "الدفعة الثالثة عند صدور حكم البداءة", "trigger_event": "judgment_first_instance",
                "amount": 3_000_000, "sequence": 3}),
        (0, 0, {"name": "الدفعة الأخيرة عند فتح ملف التنفيذ", "trigger_event": "execution_opened",
                "amount": 2_000_000, "sequence": 4}),
    ],
})
(m_contract | m_debt | m_exec).write({"engagement_id": eng_rafidain.id})
eng_rafidain.write({"line_ids": [
    (0, 0, {"name": "أتعاب دعوى الدين عند صدور الحكم", "trigger_event": "judgment_first_instance",
            "task_id": m_debt.id, "amount": 1_500_000, "sequence": 5}),
    (0, 0, {"name": "أتعاب دعوى الدين عند التنفيذ", "trigger_event": "execution_opened",
            "task_id": m_debt.id, "amount": 1_000_000, "sequence": 6}),
]})
eng_rafidain.action_ldm_activate()
env["legal.court.stage"].create({"task_id": m_contract.id, "stage": "first_instance", "department_id": karkh.id,
                                 "case_number": "1452/ب/2026", "date_filed": today - relativedelta(months=1)})

eng_ahmed = Engagement.create({
    "legal_company_id": ahmed.id, "lawyer_id": lawyer.id, "fee_type": "lump_sum", "amount": 6_000_000,
    "success_percent": 15, "currency_id": iqd.id, "date_start": today,
    "note": "أتعاب دعوى التعويض أمام محكمة البداءة فقط.",
    "line_ids": [
        (0, 0, {"name": "نصف الأتعاب عند التوقيع", "trigger_event": "signing", "amount": 3_000_000, "sequence": 1}),
        (0, 0, {"name": "النصف الثاني عند صدور الحكم", "trigger_event": "judgment_first_instance",
                "amount": 3_000_000, "sequence": 2}),
    ],
})
m_ahmed.engagement_id = eng_ahmed

eng_gulf = Engagement.create({
    "legal_company_id": gulf.id, "lawyer_id": lawyer.id, "fee_type": "retainer", "amount": 500_000,
    "currency_id": iqd.id, "date_start": today.replace(day=1) - relativedelta(months=3), "bar_withholding": True,
    "note": "مستشار قانوني للشركة: الاستشارات والعقود ومراجعة المراسلات.",
})
m_gulf.engagement_id = eng_gulf
eng_gulf.action_ldm_activate()

eng_dijla = Engagement.create({
    "legal_company_id": dijla.id, "lawyer_id": lawyer2.id, "fee_type": "hourly", "hourly_rate": 120,
    "currency_id": usd.id, "date_start": today - relativedelta(months=1), "signed": True,
})
m_dijla.engagement_id = eng_dijla
eng_dijla.action_ldm_activate()

# Expenses, client money and a runner's advance -----------------------------
Expense = env["legal.task.expense"]
Fund = env["legal.client.fund.line"]
Fund.create({"legal_company_id": rafidain.id, "task_id": m_contract.id, "kind": "deposit", "amount": 2_500_000,
             "currency_id": iqd.id, "receipt_number": "و.ق/118", "date": today - dt.timedelta(days=20),
             "note": "أمانة لرسوم الدعوى وأجور الخبير"})
Fund.create({"legal_company_id": dijla.id, "task_id": m_dijla.id, "kind": "deposit", "amount": 1_000,
             "currency_id": usd.id, "receipt_number": "و.ق/131", "date": today - dt.timedelta(days=8)})
cat = lambda code: env.ref(f"{M}.ldm_expense_category_{code}")  # noqa: E731
Expense.create({"task_id": m_contract.id, "category_id": cat("court_fee").id, "name": "رسم عريضة الدعوى",
                "amount": 1_250_000, "currency_id": iqd.id, "paid_by": "client_funds", "receipt_number": "144201",
                "date": today - dt.timedelta(days=18)})
Expense.create({"task_id": m_contract.id, "category_id": cat("expert_deposit").id, "name": "أمانة أجور الخبير القضائي",
                "amount": 750_000, "currency_id": iqd.id, "paid_by": "client_funds", "receipt_number": "144388",
                "date": today - dt.timedelta(days=9)})
Expense.create({"task_id": m_debt.id, "category_id": cat("court_fee").id, "name": "رسم الدعوى",
                "amount": 450_000, "currency_id": iqd.id, "paid_by": "office", "receipt_number": "145002",
                "date": today - dt.timedelta(days=6)})
Expense.create({"task_id": m_debt.id, "category_id": cat("publication").id, "name": "تبليغ بالنشر في جريدتين",
                "amount": 180_000, "currency_id": iqd.id, "paid_by": "office", "date": today - dt.timedelta(days=4)})

advance = env["legal.advance"].with_user(billing).create({
    "name": "رسوم ومصاريف مراجعات دوائر التنفيذ والمحاكم", "user_id": clerk.id, "amount": 500_000,
    "currency_id": iqd.id, "task_id": m_exec.id, "date": today - dt.timedelta(days=5)})
advance.with_user(billing).action_ldm_hand_over()
Expense.with_user(clerk).create({"task_id": m_exec.id, "category_id": cat("execution_fee").id,
                                 "name": "رسم فتح ملف التنفيذ", "amount": 210_000, "currency_id": iqd.id,
                                 "paid_by": "employee", "receipt_number": "ت/5510", "date": today - dt.timedelta(days=4)})
Expense.with_user(clerk).create({"task_id": m_exec.id, "category_id": cat("pension_stamp").id,
                                 "name": "طوابع صندوق تقاعد المحامين", "amount": 40_000, "currency_id": iqd.id,
                                 "paid_by": "employee", "date": today - dt.timedelta(days=4)})
Expense.with_user(clerk).create({"task_id": m_exec.id, "category_id": cat("transport").id,
                                 "name": "أجرة نقل إلى مديرية التنفيذ", "amount": 25_000, "currency_id": iqd.id,
                                 "paid_by": "employee", "date": today - dt.timedelta(days=3)})
env["legal.court.stage"].create({"task_id": m_exec.id, "stage": "execution", "department_id": execution.id,
                                 "execution_file_number": "ت/2026/881"})

# Time -----------------------------------------------------------------------
Time = env["legal.time.entry"]
for task, hours, text, days in [
    (m_contract, 1.5, "مراجعة تقرير الخبير وإعداد الاعتراض عليه", 0),
    (m_contract, 0.75, "اتصال بمدير المشاريع في الشركة حول المستندات", 0),
    (m_debt, 2.0, "إعداد لائحة الدعوى على مصرف الشمال", 0),
    (m_gulf, 1.25, "مراجعة عقد توريد المعدات وتعليقات على شروط الضمان", 1),
    (m_debt, 0.5, "متابعة التبليغ بالنشر", 1),
]:
    Time.create({"task_id": task.id, "user_id": lawyer.id, "duration": hours, "description": text,
                 "date": today - dt.timedelta(days=days), "billable": True})
for hours, text in [(3.0, "مراجعة مطالبة الشحنة وبوليصة الشحن"), (1.5, "اجتماع مع المدير المالي للشركة")]:
    entry = Time.create({"task_id": m_dijla.id, "user_id": lawyer2.id, "duration": hours, "description": text,
                         "date": today - dt.timedelta(days=2)})
    entry.action_ldm_approve()
settings = env["res.users.settings"]._find_or_create_for_user(lawyer)
settings.write({"ldm_timer_task_ref": m_debt.id,
                "ldm_timer_start": dt.datetime.now() - dt.timedelta(minutes=47, seconds=12)})

# An invoice already sent, with a partial payment ------------------------------
Billable = env["legal.billable"]
first_items = Billable.search([("legal_company_id", "=", rafidain.id), ("kind", "=", "fee")]).filtered(
    lambda row: row.fee_line_id.trigger_event in ("signing", "filing"))
Wizard = env["legal.invoice.wizard"].with_user(billing)
wizard = Wizard.create({"billable_ids": [(6, 0, first_items.ids)], "invoice_date": today - dt.timedelta(days=15)})
invoice = env["account.move"].browse(wizard.action_create()["res_id"])
invoice.action_post()
env["account.payment.register"].with_context(active_model="account.move", active_ids=invoice.ids).create(
    {"amount": 3_000_000, "payment_date": today - dt.timedelta(days=10)})._create_payments()
env.cr.flush()

# A judgment: the third instalment falls due and waits in To invoice.
env["legal.judgment"].create({"task_id": m_contract.id, "date": today - dt.timedelta(days=2),
                              "department_id": karkh.id, "court_stage": "first_instance", "result": "for",
                              "amount_awarded": 142_000_000})

# A conflict: a new client's case against our own client --------------------------
newcomer = Company.create({"name": "شركة النور للتجهيزات الطبية", "phone": "07705550011", "lawyer_id": lawyer.id,
                           "lawyer_ids": [(6, 0, [lawyer.id])]})
conflict_task = Task.browse(Task.with_user(lawyer).create_from_template({
    "template_id": commercial.id, "legal_company_id": newcomer.id, "department_id": rusafa.id,
    "name": "مطالبة بقيمة أجهزة موردة", "our_role": "plaintiff",
    "opponent_name": "شركة الرافدين للمقاولات العامة", "key_date": str(today + dt.timedelta(days=20))}))

# A matter to close with instalments still to come: the original contract is in our custody.
m_debt.document_ids[:1].write({"original_held": True})
eng_ahmed.write({"signed": True})
env.cr.commit()

base = "/odoo/action-legal_department_management."
matter_url = "/odoo/matters/%s"
screens = {
    "lawyer": [
        {"name": "l_engagement_cap", "path": f"{base}action_ldm_engagement/{eng_ahmed.id}", "wait": ".o_form_view"},
        {"name": "l_engagement_schedule", "path": f"{base}action_ldm_engagement/{eng_rafidain.id}", "wait": ".o_form_view"},
        {"name": "l_matter_money", "path": matter_url % m_contract.id, "wait": ".o_form_view",
         "clicks": [".o_notebook_headers a[name='money']"]},
        {"name": "l_matter_unsigned", "path": matter_url % m_ahmed.id, "wait": ".o_form_view",
         "clicks": [".o_notebook_headers a[name='money']"]},
        {"name": "l_conflict_banner", "path": matter_url % conflict_task.id, "wait": ".o_form_view"},
        {"name": "l_day_sheet", "path": f"{base}action_ldm_time_entry", "wait": ".o_list_view"},
        {"name": "l_timer_menu", "path": matter_url % m_contract.id, "wait": ".o_form_view",
         "clicks": [".o_ldm_timer_toggle"], "full": False},
        {"name": "l_timer_stop", "path": matter_url % m_contract.id, "wait": ".o_form_view",
         "clicks": [".o_ldm_timer_toggle", ".o_ldm_timer_panel .btn-primary"], "full": False},
        {"name": "l_close_dialog", "path": matter_url % m_debt.id, "wait": ".o_form_view",
         "clicks": ["button[name='action_set_done']", ".modal input[data-value='settled']"], "full": False},
        {"name": "l_client_message", "path": matter_url % m_contract.id, "wait": ".o_form_view",
         "clicks": ["button[name='action_ldm_message']"], "full": False},
    ],
    "billing": [
        {"name": "b_to_invoice", "path": f"{base}action_ldm_to_invoice", "wait": ".o_list_view"},
        {"name": "b_invoice_wizard", "path": f"{base}action_ldm_engagement/{eng_rafidain.id}", "wait": ".o_form_view",
         "clicks": ["button[name='action_ldm_invoice']"], "full": False},
        {"name": "b_invoice_sent", "path": f"/odoo/action-account.action_move_out_invoice_type/{invoice.id}",
         "wait": ".o_form_view"},
        {"name": "b_statement", "path": f"/report/html/legal_department_management.report_ldm_statement/{rafidain.id}",
         "wait": ".page"},
        {"name": "b_client_dossier", "path": f"/odoo/legal-clients/{rafidain.id}", "wait": ".o_form_view"},
        {"name": "b_client_money", "path": f"{base}action_ldm_client_fund", "wait": ".o_list_view"},
        {"name": "b_advance_settle", "path": f"{base}action_ldm_advance/{advance.id}", "wait": ".o_form_view",
         "clicks": ["button[name='action_ldm_settle']"], "full": False},
        {"name": "b_fee_agreements", "path": f"{base}action_ldm_engagement", "wait": ".o_list_view"},
        {"name": "b_fee_agreement_pdf", "path": f"/report/html/legal_department_management.report_ldm_engagement/{eng_rafidain.id}",
         "wait": ".page"},
    ],
    "manager": [
        {"name": "p_engagement_cap", "path": f"{base}action_ldm_engagement/{eng_ahmed.id}", "wait": ".o_form_view"},
        {"name": "p_conflict_banner", "path": matter_url % conflict_task.id, "wait": ".o_form_view"},
        {"name": "p_conflict_decide", "path": matter_url % conflict_task.id, "wait": ".o_form_view",
         "clicks": [".alert button[name='action_ldm_open_conflict']"], "full": False},
        {"name": "p_conflict_checks", "path": f"{base}action_ldm_conflict_check", "wait": ".o_list_view"},
    ],
    "clerk_phone": [
        {"name": "advance", "path": f"{base}action_ldm_advance/{advance.id}", "wait": ".o_form_view"},
        {"name": "expense_new", "path": f"{base}action_ldm_expense/new", "wait": ".o_form_view"},
        {"name": "expenses", "path": f"{base}action_ldm_expense", "wait": ".o_action_manager > *"},
    ],
    "lawyer_phone": [
        {"name": "matter_money", "path": matter_url % m_contract.id, "wait": ".o_form_view",
         "clicks": [".o_notebook_headers a[name='money']"]},
        {"name": "client_message", "path": matter_url % m_contract.id, "wait": ".o_form_view",
         "clicks": ["button[name='action_ldm_message']"], "full": False},
        {"name": "timer_menu", "path": matter_url % m_contract.id, "wait": ".o_form_view",
         "clicks": [".o_ldm_timer_toggle"], "full": False},
    ],
}
for role, items in screens.items():
    with open(os.path.join(OUT, f"screens-{role}.json"), "w", encoding="utf-8") as handle:
        json.dump(items, handle, ensure_ascii=False, indent=1)
print("money demo ready:", {
    "matters": Task.search_count([]), "engagements": Engagement.search_count([]),
    "to_invoice": Billable.search_count([]), "invoice": invoice.name, "conflict_matter": conflict_task.task_number,
    "conflict_state": conflict_task.ldm_conflict_state, "conflict_task_state": conflict_task.state,
})
