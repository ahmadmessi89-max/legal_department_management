# Run in `odoo-bin shell` on a local database with the module installed:
#   odoo-bin shell -c odoo19_ldm_reg.conf -d ldm_r < docs/ldm/tools/seed_reg.py
# Iraqi demo data for the registers' screens (stream R): powers of attorney,
# correspondence, letter templates, requests, opinions, letters of guarantee and
# the reports. Local users only: login = password, Arabic, Baghdad time.
# Writes the ids it created to docs/ldm/evidence/03-reg/seed_ids.json.
import datetime as dt
import json
import os

M = "legal_department_management"
today = dt.date.today()
D = dt.timedelta

env["res.config.settings"]._ldm_apply_preset("department")
calendar = env.ref(f"{M}.ldm_calendar_iraq")
env.company.ldm_calendar_id = calendar
env["res.lang"]._activate_lang("ar_001")
env.ref("base.user_admin").write({"lang": "ar_001", "tz": "Asia/Baghdad"})
env.ref("base.user_admin").group_ids = [(4, env.ref(f"{M}.group_legal_manager").id)]


def user(login, name, *groups):
    Users = env["res.users"].with_context(no_reset_password=True)
    found = Users.search([("login", "=", login)], limit=1)
    values = {"name": name, "login": login, "password": login, "lang": "ar_001", "tz": "Asia/Baghdad",
              "group_ids": [(6, 0, [env.ref("base.group_user").id] + [env.ref(g).id for g in groups])]}
    if found:
        found.write(values)
        return found
    return Users.create(values)


clerk = user("reg_clerk", "حيدر كاظم (معقّب)", f"{M}.group_ldm_clerk")
lawyer = user("reg_lawyer", "المحامية زينب الجبوري", f"{M}.group_legal_user")
lawyer2 = user("reg_lawyer2", "المحامي علي الساعدي", f"{M}.group_legal_user")
approver = user("reg_approver", "د. سعد الربيعي (معتمِد)", f"{M}.group_ldm_approver")
manager = user("reg_manager", "المستشار مصطفى العبيدي", f"{M}.group_legal_manager")
auditor = user("reg_auditor", "المدقق نور الهدى", f"{M}.group_ldm_auditor")
employee = user("reg_employee", "سارة محمود (قسم المشتريات)")

# Bodies and courts ---------------------------------------------------------
Ministry, Department = env["legal.ministry"], env["legal.department"]


def ministry(name, **values):
    return Ministry.search([("name", "=", name)], limit=1) or Ministry.create(dict(values, name=name))


def body(name, parent, **values):
    return Department.search([("name", "=", name)], limit=1) or Department.create(
        dict(values, name=name, ministry_id=parent.id))


council = ministry("مجلس القضاء الأعلى", body_kind="judicial")
trade = ministry("وزارة التجارة")
finance = ministry("وزارة المالية")
justice = ministry("وزارة العدل")
karkh = body("محكمة بداءة الكرخ", council, body_kind="court", court_degree="first_instance",
             addressee_title="السيد رئيس محكمة بداءة الكرخ المحترم")
registry = body("دائرة تسجيل الشركات", trade, addressee_title="السيد مدير عام دائرة تسجيل الشركات المحترم")
tax = body("الهيئة العامة للضرائب", finance, addressee_title="السيد مدير عام الهيئة العامة للضرائب المحترم")
notary = body("كاتب عدل الكرخ الأول", justice, body_kind="notary")

# Clients ---------------------------------------------------------------------
Company = env["legal.company"]


def client(name, owner, **values):
    return Company.search([("name", "=", name)], limit=1) or Company.create(dict(
        values, name=name, lawyer_id=owner.id, lawyer_ids=[(6, 0, [owner.id])]))


rafidain = client("شركة الرافدين للمقاولات العامة", lawyer, registration_number="م.ش/45871", tax_number="300145782",
                  owner_name="عماد حسن الموسوي", entity_type="مقاولات إنشائية", address="بغداد - الكرادة - شارع 62",
                  phone="07701234567")
tigris = client("مجموعة دجلة التجارية", lawyer, registration_number="م.ش/51120", owner_name="رنا عبد الكريم")
nineveh = client("شركة نينوى للصناعات الغذائية", lawyer2, registration_number="م.ش/38814")

# Matters ---------------------------------------------------------------------
Task = env["legal.task"]
gov_t = env.ref(f"{M}.ldm_template_government")
suit_t = env.ref(f"{M}.ldm_template_civil_lawsuit")
opinion_t = env.ref(f"{M}.ldm_template_opinion")


def matter(values):
    return Task.browse(Task.with_user(lawyer).create_from_template(values))


gov = matter({"template_id": gov_t.id, "legal_company_id": rafidain.id, "department_id": registry.id,
              "name": "تجديد شهادة تسجيل الشركة لسنة 2026", "reference": "ت.ش/9921"})
gov.step_ids[:1].write({"state": "done", "done_date": today - D(days=2), "done_by_id": clerk.id,
                        "receipt_number": "771245"})
gov.write({"lawyer_ids": [(4, clerk.id)]})
env["legal.task.expense"].create({"task_id": gov.id, "name": "رسم تجديد الشهادة", "amount": 25000,
                                  "receipt_number": "771245", "date": today - D(days=2)})
env["legal.task.expense"].create({"task_id": gov.id, "name": "طابع تقاعد", "amount": 5000, "date": today - D(days=2)})
gov.sudo().action_details = "الموظف المختص في الطابق الثاني طلب نسخة مصدقة من عقد التأسيس."

suit = matter({"template_id": suit_t.id, "legal_company_id": rafidain.id, "department_id": karkh.id,
               "name": "دعوى استرداد مستحقات مقاولة مدرسة الكرخ", "our_role": "plaintiff",
               "opponent_name": "شركة البيان للتجهيزات", "key_date": str(today + D(days=5))})
suit.write({"matter_value": 45000000, "court_case_number": "1834/ب/2026", "court_stage": "first_instance"})
against = matter({"template_id": suit_t.id, "legal_company_id": tigris.id, "department_id": karkh.id,
                  "name": "دعوى تعويض مقامة من مورد سابق", "our_role": "defendant",
                  "opponent_name": "مكتب الفرات للتوريدات", "key_date": str(today + D(days=12))})
against.write({"matter_value": 120000000, "court_case_number": "2210/ب/2026"})
env["legal.hearing"].create({"task_id": suit.id, "date": today - D(days=6), "state": "held", "kind": "hearing",
                             "department_id": karkh.id, "attending_user_id": lawyer.id, "outcome": "adjourned"})
judgment = env["legal.judgment"].create({"task_id": suit.id, "date": today - D(days=3), "result": "for",
                                         "amount_awarded": 30000000, "department_id": karkh.id,
                                         "court_degree": "first_instance"})
env["legal.deadline"].create({"task_id": suit.id, "name": "مدة الاستئناف (30 يوماً من التبليغ)", "kind": "appeal",
                              "judgment_id": judgment.id, "date_safe": today + D(days=24),
                              "date_deadline": today + D(days=24), "user_id": lawyer.id})
env["legal.deadline"].create({"task_id": against.id, "name": "مدة الاعتراض على الحكم الغيابي", "kind": "appeal",
                              "date_safe": today - D(days=4), "date_deadline": today - D(days=4), "state": "missed",
                              "user_id": lawyer.id})

# Powers of attorney -----------------------------------------------------------
Poa = env["legal.poa"].with_user(lawyer)


def poa(values):
    found = env["legal.poa"].search([("number", "=", values["number"])], limit=1)
    return found or Poa.create(values)


poa_suit = poa({"principal_company_id": rafidain.id, "poa_type": "judicial", "number": "3317",
                "notary_office": "كاتب عدل الكرخ الأول", "date_issued": today - D(days=340),
                "date_expiry": today + D(days=12), "agent_user_ids": [(6, 0, [lawyer.id, lawyer2.id])],
                "scope": "المرافعة والمدافعة أمام المحاكم كافة بدرجاتها، والطعن في الأحكام، والصلح والإقرار.",
                "substitution_allowed": True, "original_location": "خزانة القسم القانوني - الملف 14"})
suit.poa_id = poa_suit
poa_general = poa({"principal_company_id": rafidain.id, "poa_type": "general", "number": "5120",
                   "notary_office": "كاتب عدل الكرادة", "date_issued": today - D(days=60),
                   "date_expiry": today + D(days=300), "agent_user_ids": [(6, 0, [lawyer.id])],
                   "body_ids": [(6, 0, [registry.id, tax.id])],
                   "scope": "مراجعة دوائر الدولة كافة وإنجاز المعاملات باسم الشركة."})
poa_runner = poa({"principal_company_id": rafidain.id, "poa_type": "authorisation", "number": "ت/88",
                  "date_issued": today - D(days=20), "date_expiry": today + D(days=160),
                  "agent_user_ids": [(6, 0, [clerk.id])], "body_ids": [(6, 0, [registry.id])],
                  "scope": "تخويل بمراجعة دائرة تسجيل الشركات لتجديد الشهادة واستلامها."})
poa_old = poa({"principal_company_id": tigris.id, "poa_type": "special", "number": "2204",
               "notary_office": "كاتب عدل المنصور", "date_issued": today - D(days=400),
               "date_expiry": today - D(days=15), "agent_user_ids": [(6, 0, [lawyer.id])]})
poa_revoked = poa({"principal_company_id": tigris.id, "poa_type": "judicial", "number": "2931",
                   "notary_office": "كاتب عدل المنصور", "date_issued": today - D(days=90),
                   "date_expiry": today + D(days=200), "agent_user_ids": [(6, 0, [lawyer.id])]})
against.poa_id = poa_revoked
if poa_revoked.state != "revoked":
    poa_revoked._ldm_revoke(today - D(days=1), "عزل الوكيل بموجب الإنذار العدلي المرقم 4471 في "
                            + str(today - D(days=1)) + " بطلب من الموكّل.")

# Correspondence ---------------------------------------------------------------
Letter = env["legal.correspondence"]
if not Letter.search_count([("name", "=", "طلب تزويدنا ببراءة ذمة ضريبية لشركة الرافدين")]):
    incoming = Letter.with_user(clerk).create({
        "name": "طلب تزويدنا ببراءة ذمة ضريبية لشركة الرافدين", "direction": "incoming", "date": today - D(days=1),
        "received_date": today - D(days=1), "department_id": tax.id, "legal_company_id": rafidain.id,
        "sender_ref": "ض/4417", "sender_date": today - D(days=4), "referred_by": "المدير القانوني",
        "referral_note": "للإجابة خلال ثلاثة أيام وتزويدهم بالمستمسكات المطلوبة.", "assigned_user_id": lawyer.id,
        "reply_days": 3})
    incoming.action_register()
    answered = Letter.with_user(clerk).create({
        "name": "استفسار عن موقف دعوى شركة دجلة", "direction": "incoming", "date": today - D(days=20),
        "received_date": today - D(days=20), "department_id": karkh.id, "legal_company_id": tigris.id,
        "sender_ref": "ب/991", "reply_days": 5})
    answered.action_register()
    template = env.ref(f"{M}.ldm_letter_to_body")
    doc_wizard = env["legal.document.wizard"].with_user(lawyer).with_context(default_task_id=gov.id).create({
        "template_id": template.id, "lang": "ar_001", "signatory_title": "المحامية - وكيلة الشركة"})
    doc_wizard._onchange_render()
    outgoing = Letter.browse(doc_wizard.action_create()["res_id"])
    outgoing.write({"cc_lines": "شركة الرافدين للمقاولات العامة - للعلم\nالملف", "reply_days": 7})
    outgoing.with_user(clerk).action_register()
    reply = Letter.with_user(clerk).create({
        "name": "موقف دعوى شركة دجلة", "direction": "outgoing", "date": today - D(days=15),
        "department_id": karkh.id, "legal_company_id": tigris.id, "reply_to_id": answered.id, "lang": "ar_001",
        "body_html": "<p>جواباً على كتابكم، نعلمكم بأن الدعوى ما زالت قيد المرافعة، والجلسة القادمة محددة.</p>",
        "signatory_id": lawyer.id, "signatory_title": "المحامية"})
    reply.action_register()
    wrong = Letter.with_user(clerk).create({"name": "طلب نسخة من قرار التسجيل", "direction": "outgoing",
                                            "date": today - D(days=10), "department_id": registry.id,
                                            "body_html": "<p>يرجى تزويدنا بنسخة.</p>"})
    wrong.action_register()
    wrong._ldm_void("أُرسل إلى الدائرة الخطأ؛ حلّ محله الكتاب اللاحق.")
    Letter.with_user(clerk).create({"name": "طلب تحديد موعد لمراجعة الملف", "direction": "outgoing",
                                    "department_id": registry.id, "task_id": gov.id, "lang": "ar_001",
                                    "body_html": "<p>نرجو تحديد موعد لمراجعة ملف الشركة.</p>"})

# Requests from other departments ----------------------------------------------
Request = env["legal.request"].with_user(employee)
if not env["legal.request"].search_count([("requester_id", "=", employee.id)]):
    Request.create({"name": "مراجعة عقد توريد مواد غذائية مع شركة النهرين", "request_type": "contract",
                    "needed_by": today + D(days=6),
                    "description": "العقد بقيمة 180 مليون دينار ومدته سنة، والتوقيع يوم الأحد القادم."})
    returned = Request.create({"name": "رأي في فسخ عقد إيجار المخزن في البصرة", "request_type": "opinion",
                               "needed_by": today + D(days=10), "description": "المؤجر تأخر في الصيانة."})
    returned.with_user(lawyer).action_ldm_take()
    returned.with_user(lawyer)._ldm_return("يرجى إرفاق نسخة عقد الإيجار الموقّع وآخر مراسلة مع المؤجر.")
    accepted = Request.create({"name": "تجديد وكالة المعقّب لدى دائرة التسجيل", "request_type": "poa",
                               "needed_by": today + D(days=14), "description": "الوكالة الحالية تنتهي قريباً."})
    accepted.with_user(lawyer).action_ldm_take()
    wizard = env["legal.reg.matter.wizard"].with_user(lawyer).with_context(default_request_id=accepted.id).create(
        {"legal_company_id": rafidain.id, "department_id": notary.id})
    wizard.action_create()
    declined = Request.create({"name": "هل نختار المورّد الأرخص أم الأسرع؟", "request_type": "other",
                               "description": "مفاضلة بين عرضين."})
    declined.with_user(lawyer)._ldm_decline("قرار تجاري يعود لقسم المشتريات وليس سؤالاً قانونياً.")
    in_review = Request.create({"name": "إنذار مستأجر متأخر عن دفع بدل الإيجار", "request_type": "dispute",
                                "needed_by": today + D(days=3), "description": "المستأجر متأخر ثلاثة أشهر."})
    in_review.with_user(lawyer).action_ldm_take()

# Opinions -------------------------------------------------------------------------
if not Task.search_count([("kind", "=", "opinion"), ("opinion_number", "!=", False)]):
    op = Task.browse(Task.with_user(lawyer).create_from_template({
        "template_id": opinion_t.id, "legal_company_id": rafidain.id,
        "name": "مدى جواز فسخ عقد المقاولة لتأخر صاحب العمل في الدفع",
        "lawyer_ids": [(4, approver.id)]}))
    op.write({"requesting_unit": "قسم العقود",
              "question": "هل يحق للشركة التوقف عن التنفيذ وفسخ العقد إذا تأخر صاحب العمل عن دفع السلف المستحقة؟",
              "opinion_html": "<p>يحق للمقاول الامتناع عن التنفيذ استناداً إلى الدفع بعدم التنفيذ (المادة 280 من القانون "
                              "المدني العراقي)، على أن يُنذر صاحب العمل رسمياً قبل ذلك. أما الفسخ فيكون بطلب من المحكمة "
                              "(المادة 177) ما لم ينص العقد على الفسخ الاتفاقي.</p>"})
    if op.approval_state == "to_approve":
        op.with_user(approver).action_approve()
    op.with_user(approver).action_issue_opinion()
    draft_op = Task.browse(Task.with_user(lawyer).create_from_template({
        "template_id": opinion_t.id, "legal_company_id": tigris.id,
        "name": "الأثر القانوني لتغيير المدير المفوض على الوكالات القائمة", "lawyer_ids": [(4, approver.id)]}))
    draft_op.write({"requesting_unit": "مكتب المدير المفوض",
                    "question": "هل تبقى الوكالات الصادرة عن المدير المفوض السابق نافذة بعد تغييره؟"})

# Letters of guarantee ----------------------------------------------------------------
Guarantee = env["legal.guarantee"].with_user(lawyer)
bank = env["res.partner"].search([("name", "=", "مصرف الرافدين")], limit=1) or env["res.partner"].create(
    {"name": "مصرف الرافدين", "is_company": True})
bank2 = env["res.partner"].search([("name", "=", "مصرف بغداد")], limit=1) or env["res.partner"].create(
    {"name": "مصرف بغداد", "is_company": True})
water = env["res.partner"].search([("name", "=", "وزارة الموارد المائية")], limit=1) or env["res.partner"].create(
    {"name": "وزارة الموارد المائية", "is_company": True})
if not env["legal.guarantee"].search_count([]):
    Guarantee.create({"name": "ضمان حسن تنفيذ - مشروع محطة ماء البصرة", "kind": "performance", "number": "LG-2026-778",
                      "bank_id": bank.id, "beneficiary_id": water.id, "amount": 150000000, "percent": 5,
                      "legal_company_id": rafidain.id, "date_issued": today - D(days=200),
                      "date_expiry": today + D(days=18)})
    Guarantee.create({"name": "ضمان دخول مناقصة - تأهيل طريق الكوت", "kind": "bid", "number": "BG-5521",
                      "bank_id": bank2.id, "beneficiary_id": water.id, "amount": 25000000,
                      "legal_company_id": rafidain.id, "date_issued": today - D(days=10),
                      "date_expiry": today + D(days=120)})
    released = Guarantee.create({"name": "ضمان سلفة تشغيلية - مجمع دجلة السكني", "kind": "advance_payment",
                                 "number": "AP-3310", "bank_id": bank.id, "amount": 60000000,
                                 "legal_company_id": tigris.id, "date_expiry": today + D(days=40)})
    released.write({"state": "released", "release_date": today - D(days=5)})

# A company document expiring soon, for the monthly report --------------------------
doc_type = env["legal.document.type"].search([], limit=1) or env["legal.document.type"].create(
    {"name": "هوية غرفة التجارة", "category": "chamber", "validity": "expiry_date"})
if not env["legal.company.document"].search_count([]):
    env["legal.company.document"].create({"legal_company_id": rafidain.id, "document_type_id": doc_type.id,
                                          "number": "غ.ت/10442", "date_expiry": today + D(days=40)})

env["legal.task"]._ldm_run_reminders()
env.cr.commit()

ids = {
    "gov": gov.id, "suit": suit.id, "against": against.id,
    "poa_suit": poa_suit.id, "poa_general": poa_general.id, "poa_runner": poa_runner.id,
    "poa_revoked": poa_revoked.id, "rafidain": rafidain.id, "tigris": tigris.id,
    "incoming": Letter.search([("name", "=", "طلب تزويدنا ببراءة ذمة ضريبية لشركة الرافدين")], limit=1).id,
    "outgoing": Letter.search([("task_id", "=", gov.id), ("state", "=", "registered")], limit=1).id,
    "draft_letter": Letter.search([("state", "=", "draft")], limit=1).id,
    "opinion": Task.search([("kind", "=", "opinion"), ("opinion_number", "!=", False)], limit=1).id,
    "request_returned": env["legal.request"].search([("state", "=", "returned")], limit=1).id,
    "request_new": env["legal.request"].search([("state", "=", "new")], limit=1).id,
    "request_review": env["legal.request"].search([("state", "=", "in_review")], limit=1).id,
    "request_accepted": env["legal.request"].search([("state", "=", "accepted")], limit=1).id,
    "guarantee": env["legal.guarantee"].search([("number", "=", "LG-2026-778")], limit=1).id,
}
out = os.path.join("docs", "ldm", "evidence", "03-reg")
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, "seed_ids.json"), "w", encoding="utf-8") as handle:
    json.dump(ids, handle, indent=1)
print("registers seed ready:", ids)
