# Workspace stream (W) demo data for screenshots. Run in `odoo-bin shell` on
# ldm_w after installing the module:
#   odoo-bin shell -c odoo19_ldm_ws.conf -d ldm_w --no-http < docs/ldm/tools/seed_ws.py
#
# Creates one user per role (login = password, local database only), Iraqi
# clients, bodies and courts, and matters dated around today so that every
# band of My Day, the agenda, the cockpit and the approvals inbox has rows.
# Not module data: nothing here ships.
import datetime as dt

from odoo import fields

M = "legal_department_management"
today = fields.Date.context_today(env["res.users"].with_context(tz="Asia/Baghdad"))


def day(offset):
    return today + dt.timedelta(days=offset)


Users = env["res.users"].with_context(no_reset_password=True)
if Users.search([("login", "=", "zainab")]):
    raise SystemExit("seed_ws already ran on this database")

env["res.config.settings"]._ldm_apply_preset("hybrid")
env.company.name = "مجموعة سومر القابضة — القسم القانوني"


def make_user(login, name, group):
    return Users.create({
        "login": login, "password": login, "name": name, "lang": "ar_001", "tz": "Asia/Baghdad",
        "email": f"{login}@legal.iq",
        "group_ids": [(6, 0, [env.ref("base.group_user").id, env.ref(f"{M}.{group}").id])],
    })


zainab = make_user("zainab", "زينب عبد الله", "group_legal_user")
ali = make_user("ali", "علي حسن", "group_ldm_clerk")
hussein = make_user("hussein", "حسين كاظم", "group_ldm_approver")
sara = make_user("sara", "سارة محمود", "group_legal_manager")
mustafa = make_user("mustafa", "مصطفى جواد", "group_ldm_auditor")
karim = make_user("karim", "كريم فاضل", "group_legal_user")

# Matter types in Arabic (the English source stays; ar_001 readers see these).
arabic_types = {
    "ldm_template_government": ("معاملة حكومية", ["جمع المستمسكات", "تقديم الملف في الشباك", "متابعة المعاملة واستلام النتيجة"]),
    "ldm_template_civil_lawsuit": ("دعوى مدنية", ["تحرير عريضة الدعوى", "دفع الرسم وتسجيل الدعوى", "متابعة تبليغ المدعى عليه"]),
    "ldm_template_commercial_lawsuit": ("دعوى تجارية", ["تحرير عريضة الدعوى", "دفع الرسم وتسجيل الدعوى"]),
    "ldm_template_labour_case": ("دعوى عمالية", []),
    "ldm_template_contract_review": ("مراجعة عقد", ["مراجعة العقد وإرسال الملاحظات", "الاتفاق على النص النهائي"]),
    "ldm_template_opinion": ("رأي قانوني", ["البحث وكتابة مسودة الرأي", "إصدار الرأي"]),
    "ldm_template_poa": ("وكالة لدى كاتب العدل", ["إعداد نص الوكالة", "التوقيع لدى كاتب العدل"]),
    "ldm_template_company_amendment": ("تعديل عقد شركة", []),
    "ldm_template_execution": ("ملف تنفيذ", ["فتح الملف في مديرية التنفيذ", "متابعة تبليغ الإخطار التنفيذي"]),
}
for xmlid, (name, steps) in arabic_types.items():
    template = env.ref(f"{M}.{xmlid}")
    template.update_field_translations("name", {"ar_001": name})
    for line, arabic in zip(template.step_ids, steps):
        line.update_field_translations("name", {"ar_001": arabic})
amendment = env.ref(f"{M}.ldm_template_company_amendment")
amendment.requires_approval = True
amendment.step_ids = [(0, 0, {"sequence": 10, "name": "Draft the amendment", "offset_days": 2, "offset_from": "start"}),
                      (0, 0, {"sequence": 20, "name": "Register it at the companies registry", "offset_days": 3,
                              "is_visit": True})]
for line, arabic in zip(amendment.step_ids, ["صياغة قرار التعديل", "تسجيل التعديل في دائرة تسجيل الشركات"]):
    line.update_field_translations("name", {"ar_001": arabic})

# Bodies and courts.
Ministry, Department = env["legal.ministry"], env["legal.department"]
council = Ministry.create({"name": "مجلس القضاء الأعلى", "body_kind": "judicial"})
trade = Ministry.create({"name": "وزارة التجارة"})
finance = Ministry.create({"name": "وزارة المالية"})
justice = Ministry.create({"name": "وزارة العدل"})
karkh = Department.create({"name": "محكمة بداءة الكرخ", "ministry_id": council.id, "body_kind": "court",
                           "court_degree": "first_instance", "address": "بغداد، الكرخ، شارع حيفا"})
rusafa = Department.create({"name": "محكمة بداءة الرصافة", "ministry_id": council.id, "body_kind": "court",
                            "court_degree": "first_instance"})
labour = Department.create({"name": "محكمة العمل في بغداد", "ministry_id": council.id, "body_kind": "court",
                            "court_degree": "labour"})
execution = Department.create({"name": "مديرية تنفيذ الكرخ", "ministry_id": justice.id, "body_kind": "execution"})
registry = Department.create({"name": "دائرة تسجيل الشركات", "ministry_id": trade.id, "body_kind": "registry",
                              "address": "بغداد، المنصور، قرب ساحة الرواد", "working_hours": "٨:٠٠ – ١٤:٣٠"})
tax = Department.create({"name": "الهيئة العامة للضرائب — فرع الكرادة", "ministry_id": finance.id,
                         "address": "بغداد، الكرادة داخل", "working_hours": "٨:٣٠ – ١٤:٠٠"})
notary = Department.create({"name": "كاتب عدل المنصور", "ministry_id": justice.id, "body_kind": "notary"})

# Document types and documents to collect for government matters.
DocType = env["legal.document.type"]
id_card = DocType.create({"name": "البطاقة الوطنية للمدير المفوض", "category": "identity", "validity": "expiry_date"})
founding = DocType.create({"name": "شهادة تأسيس الشركة", "category": "registry"})
mandate = DocType.create({"name": "كتاب تخويل مصدّق", "category": "poa", "validity": "freshness_days",
                          "validity_days": 30})
old_clearance = DocType.create({"name": "براءة الذمة الضريبية للسنة السابقة", "category": "tax"})
government = env.ref(f"{M}.ldm_template_government")
government.document_ids = [(0, 0, {"document_type_id": t.id, "mandatory": True})
                           for t in (id_card, founding, mandate, old_clearance)]

# Clients.
Company = env["legal.company"]
rafidain = Company.create({"name": "شركة الرافدين للمقاولات العامة", "lawyer_id": zainab.id,
                           "lawyer_ids": [(6, 0, [zainab.id, ali.id])], "registration_number": "م.ش/2011/4471",
                           "phone": "07701234567"})
dijla = Company.create({"name": "مجموعة دجلة التجارية", "lawyer_id": zainab.id, "lawyer_ids": [(6, 0, [zainab.id])]})
babil = Company.create({"name": "شركة بابل للصناعات الغذائية", "lawyer_id": zainab.id,
                        "lawyer_ids": [(6, 0, [zainab.id])]})
ninawa = Company.create({"name": "شركة نينوى للنقل البري", "lawyer_id": karim.id, "lawyer_ids": [(6, 0, [karim.id])]})
ahmed = Company.create({"name": "السيد أحمد عبد الكريم", "client_kind": "individual", "lawyer_id": karim.id,
                        "lawyer_ids": [(6, 0, [karim.id])]})

Task = env["legal.task"]
Step = env["legal.task.step"]


def open_matter(user, **vals):
    task_id = Task.with_user(user).create_from_template(vals)
    return Task.browse(task_id)


def step_dates(task, offsets, user=None):
    for step, offset in zip(task.step_ids.sorted("sequence"), offsets):
        values = {"date_due": day(offset) if offset is not None else False}
        if user:
            values["user_id"] = user.id
        step.write(values)


# 1. Annual tax clearance: the runner's visits today, one late, documents to carry.
tax_file = open_matter(zainab, template_id=government.id, legal_company_id=rafidain.id, department_id=tax.id,
                       name="براءة ذمة ضريبية سنوية لعام 2026")
step_dates(tax_file, [-3, -1, 4], user=ali)
tax_file.step_ids.sorted("sequence")[0].write({"state": "done", "done_date": day(-3), "done_by_id": ali.id})
docs = tax_file.document_ids.sorted("sequence")
docs[0].write({"state": "received", "received_date": day(-3), "expiry_date": day(400)})
docs[1].write({"state": "verified", "received_date": day(-3)})
tax_file.write({"waiting_on": "body", "date_submitted": day(-6), "reference": "ض/2026/5541"})

# 2. Company registration amendment: needs approval (sent by the lawyer).
amend = open_matter(zainab, template_id=amendment.id, legal_company_id=dijla.id, department_id=registry.id,
                    name="تعديل عقد تأسيس مجموعة دجلة — زيادة رأس المال", matter_value=250000000)
amend2 = open_matter(zainab, template_id=amendment.id, legal_company_id=rafidain.id, department_id=registry.id,
                     name="تعديل نشاط شركة الرافدين وإضافة فرع البصرة")

# 3. Civil lawsuit with sessions (one held late without its outcome, one today), a deadline and an expense.
suit = open_matter(zainab, template_id=env.ref(f"{M}.ldm_template_civil_lawsuit").id, legal_company_id=dijla.id,
                   department_id=karkh.id, name="دعوى مطالبة بقيمة عقد توريد", our_role="plaintiff",
                   opponent_name="شركة الفرات للتجهيزات", key_date=str(day(0)), matter_value=180000000,
                   is_urgent=True)
suit.step_ids.sorted("sequence")[0].write({"state": "done", "done_date": day(-20), "done_by_id": zainab.id})
suit.step_ids.sorted("sequence")[1].write({"state": "done", "done_date": day(-15), "done_by_id": zainab.id})
suit.step_ids.sorted("sequence")[2].write({"date_due": day(2)})
suit.hearing_ids.write({"time": 10.0})
env["legal.hearing"].create({"task_id": suit.id, "date": day(-7), "time": 9.5, "department_id": karkh.id,
                             "attending_user_id": zainab.id, "state": "held", "outcome": "adjourned"})
env["legal.court.stage"].create({"task_id": suit.id, "stage": "first_instance", "department_id": karkh.id,
                                 "case_number": "1834/ب/2026", "case_year": 2026, "date_filed": day(-25)})
suit.write({"court_stage": "first_instance", "court_case_number": "1834/ب/2026"})
env["legal.task.expense"].create({"task_id": suit.id, "name": "رسم الدعوى", "amount": 150000, "date": day(-15),
                                  "receipt_number": "و/88213"})
env["legal.task.expense"].create({"task_id": suit.id, "name": "أجور خبير", "amount": 350000, "date": day(-8)})

# 4. Commercial lawsuit: session yesterday still waiting for its outcome.
commercial = open_matter(zainab, template_id=env.ref(f"{M}.ldm_template_commercial_lawsuit").id,
                         legal_company_id=babil.id, department_id=rusafa.id,
                         name="دعوى فسخ عقد توزيع حصري", our_role="defendant",
                         opponent_name="شركة الخليج للتسويق", key_date=str(day(-1)))
commercial.step_ids.write({"state": "done", "done_date": day(-30), "done_by_id": zainab.id})
commercial.hearing_ids.write({"time": 11.0})
env["legal.hearing"].create({"task_id": commercial.id, "date": day(4), "time": 9.0, "department_id": rusafa.id,
                             "attending_user_id": zainab.id})
env["legal.court.stage"].create({"task_id": commercial.id, "stage": "first_instance", "department_id": rusafa.id,
                                 "case_number": "922/ت/2026"})
commercial.write({"court_stage": "first_instance", "court_case_number": "922/ت/2026"})

# 5. A judgment given, waiting for its notification date, and an appeal window running.
older = open_matter(zainab, template_id=env.ref(f"{M}.ldm_template_civil_lawsuit").id, legal_company_id=babil.id,
                    department_id=karkh.id, name="دعوى تعويض عن أضرار شحنة", our_role="plaintiff",
                    opponent_name="شركة النورس للشحن")
older.step_ids.write({"state": "done", "done_date": day(-60), "done_by_id": zainab.id})
env["legal.court.stage"].create({"task_id": older.id, "stage": "first_instance", "department_id": karkh.id,
                                 "case_number": "411/ب/2026"})
env["legal.court.stage"].create({"task_id": older.id, "stage": "appeal", "case_number": "77/س/2026"})
older.write({"court_stage": "appeal", "court_case_number": "77/س/2026"})
judgment = env["legal.judgment"].create({"task_id": older.id, "date": day(-3), "department_id": karkh.id,
                                         "court_degree": "first_instance", "court_stage": "first_instance",
                                         "result": "partial", "law": "civil", "amount_awarded": 42000000})
env["legal.deadline"].create({"task_id": older.id, "judgment_id": judgment.id, "name": "مدة الاستئناف",
                              "kind": "appeal", "state": "awaiting_service", "user_id": zainab.id,
                              "company_id": env.company.id})
env["legal.deadline"].create({"task_id": suit.id, "name": "مدة الرد على اللائحة", "kind": "reply",
                              "date_start": day(-4), "date_safe": day(3), "date_deadline": day(5),
                              "user_id": zainab.id, "state": "open", "company_id": env.company.id})

# 6. Contract review due today, legal opinion this week, notary visit tomorrow.
contract = open_matter(zainab, template_id=env.ref(f"{M}.ldm_template_contract_review").id,
                       legal_company_id=rafidain.id, name="مراجعة عقد إيجار مخزن في الزعفرانية")
step_dates(contract, [0, 3])
opinion = open_matter(zainab, template_id=env.ref(f"{M}.ldm_template_opinion").id, legal_company_id=dijla.id,
                      name="رأي قانوني في شرط التحكيم مع المورد التركي")
step_dates(opinion, [5, 8])
poa = open_matter(zainab, template_id=env.ref(f"{M}.ldm_template_poa").id, legal_company_id=babil.id,
                  department_id=notary.id, name="وكالة عامة للمدير المفوض الجديد")
step_dates(poa, [-2, 1])
poa.step_ids.sorted("sequence")[0].write({"state": "done", "done_date": day(-2), "done_by_id": zainab.id})
poa.step_ids.sorted("sequence")[1].write({"fee_amount": 25000})

# 7. Karim's files (the manager's team view): a labour case tomorrow with nobody attending, an execution file.
labour_case = open_matter(karim, template_id=env.ref(f"{M}.ldm_template_labour_case").id, legal_company_id=ninawa.id,
                          department_id=labour.id, name="دعوى عامل مفصول — مطالبة بمستحقات", our_role="defendant",
                          opponent_name="حيدر سلمان", key_date=str(day(1)))
labour_case.hearing_ids.write({"attending_user_id": False, "time": 9.0})
exe = open_matter(karim, template_id=env.ref(f"{M}.ldm_template_execution").id, legal_company_id=ahmed.id,
                  department_id=execution.id, name="تنفيذ حكم نفقة")
step_dates(exe, [-4, 6], user=ali)

# 8. Another visit for the runner at the companies registry, and a closed matter.
reg_file = open_matter(karim, template_id=government.id, legal_company_id=ninawa.id, department_id=registry.id,
                       name="تجديد إجازة ممارسة النشاط")
step_dates(reg_file, [-2, 0, 6], user=ali)
reg_file.step_ids.sorted("sequence")[0].write({"state": "done", "done_date": day(-2), "done_by_id": ali.id})
done_file = open_matter(zainab, template_id=government.id, legal_company_id=rafidain.id, department_id=registry.id,
                        name="استخراج شهادة تأسيس مصدّقة")
done_file.step_ids.write({"state": "done", "done_date": day(-12), "done_by_id": ali.id})
done_file._ldm_close("completed", "استُلمت الشهادة")

# 9. An activity, a fee agreement, a runner's advance, a pending conflict check, a power of attorney.
suit.activity_schedule("mail.mail_activity_data_todo", summary="الاتصال بالموكل لتأكيد حضور الشاهد",
                       user_id=zainab.id, date_deadline=day(0))
env["legal.engagement"].create({"name": "اتفاق أتعاب سنوي — مجموعة دجلة", "legal_company_id": dijla.id,
                                "lawyer_id": zainab.id, "fee_type": "retainer", "amount": 3000000,
                                "retainer_period": "monthly", "signed": True, "signed_date": day(-90),
                                "state": "active"})
env["legal.advance"].create({"name": "رسوم معاملات الأسبوع", "user_id": ali.id, "amount": 250000, "state": "paid",
                             "date": day(-3)})
env["legal.conflict.check"].create({"task_id": commercial.id, "query": "شركة الخليج للتسويق", "decision": "pending",
                                    "hit_count": 1, "user_id": zainab.id,
                                    "hits": [{"label": "شركة الخليج للتسويق", "role": "موكل سابق"}]})
env["legal.poa"].create({"poa_type": "judicial", "principal_company_id": dijla.id, "number": "3321",
                         "notary_office": "كاتب عدل الكرادة", "date_issued": day(-200), "date_expiry": day(165),
                         "agent_user_ids": [(6, 0, [zainab.id])], "state": "active"})

env.cr.commit()
print("seed_ws ready:", Task.search_count([]), "matters;", "users: zainab ali hussein sara mustafa karim")
print("ids:", {"tax": tax_file.id, "amend": amend.id, "suit": suit.id, "commercial": commercial.id,
               "older": older.id, "contract": contract.id, "opinion": opinion.id, "poa": poa.id,
               "labour": labour_case.id, "exe": exe.id, "reg": reg_file.id, "done": done_file.id,
               "dijla": dijla.id, "rafidain": rafidain.id, "babil": babil.id})
