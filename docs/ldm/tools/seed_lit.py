# Run in `odoo-bin shell` on a local database with the module installed:
#   odoo-bin shell -c odoo19_ldm_lit.conf -d ldm_l --no-http < docs/ldm/tools/seed_lit.py
# Realistic Iraqi litigation data for the litigation stream's screens: courts
# of each degree, lawsuits at several stages, sessions over the coming two
# weeks, judgments with running and awaiting windows, a grievance chain, an
# execution file, a substitution and a trainee at an appeal court.
# Local users only (login = password); never run this on SAG's database.
import datetime as dt

M = "legal_department_management"
env = env(context=dict(env.context, tracking_disable=True, mail_create_nolog=True, no_reset_password=True,
                       lang="ar_001", tz="Asia/Baghdad"))
Users = env["res.users"]
if Users.search([("login", "=", "lit_lawyer")]):
    print("already seeded")
    raise SystemExit

today = dt.date(2026, 9, 24)  # a Thursday; the screenshots were taken on it
D = lambda offset: today + dt.timedelta(days=offset)


def group(xmlid):
    return env.ref(f"{M}.{xmlid}")


def user(login, name, role, **extra):
    values = {"name": name, "login": login, "password": login, "lang": "ar_001", "tz": "Asia/Baghdad",
              "group_ids": [(6, 0, [env.ref("base.group_user").id, group(role).id])]}
    values.update(extra)
    return Users.create(values)


manager = user("lit_manager", "سعد الجبوري", "group_legal_manager", ldm_licence_class="unrestricted",
               ldm_bar_number="4127")
lawyer = user("lit_lawyer", "حيدر عبد الكريم", "group_legal_user", ldm_licence_class="a", ldm_bar_number="18852")
lawyer2 = user("lit_lawyer2", "رنا الساعدي", "group_legal_user", ldm_licence_class="b", ldm_bar_number="21410")
trainee = user("lit_trainee", "زينب علي حسين", "group_legal_user", ldm_licence_class="trainee",
               ldm_bar_number="T-3319")
clerk = user("lit_clerk", "مصطفى حسن", "group_ldm_clerk")
auditor = user("lit_auditor", "نور الهدى كاظم", "group_ldm_auditor")
env.ref("base.user_admin").write({"lang": "ar_001", "tz": "Asia/Baghdad"})

company = env.company
company.ldm_calendar_id = env.ref(f"{M}.ldm_calendar_iraq")

# --- Courts and bodies --------------------------------------------------
Ministry, Department = env["legal.ministry"], env["legal.department"]
council = Ministry.search([("name", "=", "مجلس القضاء الأعلى")], limit=1) or \
    Ministry.create({"name": "مجلس القضاء الأعلى", "body_kind": "judicial"})
justice = Ministry.search([("name", "=", "وزارة العدل")], limit=1) or \
    Ministry.create({"name": "وزارة العدل", "body_kind": "ministry"})


def court(name, degree, parent=False, kind="court", ministry=council):
    found = Department.search([("name", "=", name)], limit=1)
    if found:
        return found
    return Department.create({"name": name, "ministry_id": ministry.id, "body_kind": kind, "court_degree": degree,
                              "parent_id": parent.id if parent else False, "governorate": "baghdad"})


cassation = court("محكمة التمييز الاتحادية", "cassation")
appeal_karkh = court("محكمة استئناف بغداد الكرخ الاتحادية", "appeal", cassation)
karkh = court("محكمة بداءة الكرخ", "first_instance", appeal_karkh)
rusafa = court("محكمة بداءة الرصافة", "first_instance", appeal_karkh)
felony = court("محكمة جنايات الكرخ", "felony", cassation)
labour = court("محكمة العمل في بغداد", "labour", appeal_karkh)
employees = court("محكمة قضاء الموظفين", "employee")
execution = court("مديرية تنفيذ الكرخ", "execution", kind="execution", ministry=justice)

# --- Clients --------------------------------------------------------------
Company = env["legal.company"]


def client(name, responsible, phone):
    return Company.create({"name": name, "lawyer_id": responsible.id, "phone": phone,
                           "lawyer_ids": [(6, 0, [responsible.id, manager.id])]})


rafidain = client("شركة الرافدين للمقاولات العامة", lawyer, "07701234567")
tigris = client("مجموعة دجلة التجارية", lawyer, "07809876543")
babil = client("شركة بابل للصناعات الغذائية", lawyer2, "07501112233")
nineveh = client("شركة نينوى للنقل البري", lawyer2, "07712223344")

Partner = env["res.partner"]
furat = Partner.create({"name": "شركة الفرات للإنشاءات", "is_company": True})
landlord = Partner.create({"name": "عبد الله جاسم محمد"})
supplier = Partner.create({"name": "شركة الخليج لتوريد المواد الغذائية", "is_company": True})
worker = Partner.create({"name": "أحمد كريم عباس"})
outside = Partner.create({"name": "المحامي علي فاضل التميمي"})

Task = env["legal.task"]
Hearing, Judgment, Stage = env["legal.hearing"], env["legal.judgment"], env["legal.court.stage"]
Deadline, Poa = env["legal.deadline"], env["legal.poa"]
T = lambda xmlid: env.ref(f"{M}.ldm_template_{xmlid}")


def matter(template, client_, lawyer_, name, body, role="plaintiff", opponent=None, value=0, **extra):
    task = Task.browse(Task.create_from_template({
        "template_id": T(template).id, "legal_company_id": client_.id, "lawyer_id": lawyer_.id, "name": name,
        "department_id": body.id, "our_role": role, **extra}))
    if opponent:
        env["legal.task.party"].create({"task_id": task.id, "partner_id": opponent.id,
                                        "role": "defendant" if role == "plaintiff" else "plaintiff"})
    if value:
        task.matter_value = value
    return task


def session(task, day, lawyer_, body=None, time=9.0, **extra):
    return Hearing.create({"task_id": task.id, "date": day, "time": time, "department_id": (body or task.department_id).id,
                           "attending_user_id": lawyer_.id if lawyer_ else False, **extra})


# 1. Construction claim at first instance: a session today still to record.
claim = matter("civil_lawsuit", rafidain, lawyer, "مطالبة بمستحقات عقد مقاولة مشروع مجمع الكرخ السكني", karkh,
               opponent=furat, value=850000000)
Stage.create({"task_id": claim.id, "stage": "first_instance", "department_id": karkh.id, "case_number": "1287/ب",
              "case_year": 2026, "date_filed": D(-60)})
old = session(claim, D(-14), lawyer, purpose="مرافعة")
old.write({"state": "held", "outcome": "adjourned", "attendance": "present",
           "needed_before": "جلب تقرير الخبير الهندسي", "outcome_note": "أجلت الدعوى لتقديم تقرير الخبير."})
today_session = session(claim, today, lawyer, time=9.5, purpose="تقديم تقرير الخبير", court_room="القاعة 3")
old.next_hearing_id = today_session
poa_rafidain = Poa.create({"poa_type": "judicial", "principal_company_id": rafidain.id, "number": "5521",
                           "notary_office": "كاتب عدل الكرخ", "date_issued": D(-200), "date_expiry": D(165),
                           "agent_user_ids": [(6, 0, [lawyer.id, lawyer2.id])], "substitution_allowed": True})
claim.poa_id = poa_rafidain

# 2. Eviction: judgment against us, served, the appeal window running.
eviction = matter("civil_lawsuit", tigris, lawyer, "دعوى تخلية مأجور مخزن الشورجة", rusafa, role="defendant",
                  opponent=landlord, value=120000000)
Stage.create({"task_id": eviction.id, "stage": "first_instance", "department_id": rusafa.id, "case_number": "642/ب",
              "case_year": 2026, "date_filed": D(-120)})
held = session(eviction, D(-12), lawyer, purpose="النطق بالحكم")
held.write({"state": "held", "outcome": "judgment", "attendance": "present"})
Judgment.create({"task_id": eviction.id, "hearing_id": held.id, "date": D(-12), "department_id": rusafa.id,
                 "court_degree": "first_instance", "law": "civil", "result": "against", "pronounced_in_presence": True,
                 "notified_date": D(-9), "summary": "إلزام الشركة بتخلية المخزن وتسليمه للمدعي خالياً من الشواغل."})

# 3. Supply dispute: judgment in our favour, not yet served.
supply = matter("commercial_lawsuit", babil, lawyer2, "مطالبة بقيمة شحنة مواد غذائية تالفة", karkh,
                opponent=supplier, value=64000000)
Stage.create({"task_id": supply.id, "stage": "first_instance", "department_id": karkh.id, "case_number": "1903/ب",
              "case_year": 2026, "date_filed": D(-150)})
given = session(supply, D(-4), lawyer2, purpose="النطق بالحكم")
given.write({"state": "held", "outcome": "judgment", "attendance": "present"})
Judgment.create({"task_id": supply.id, "hearing_id": given.id, "date": D(-4), "department_id": karkh.id,
                 "court_degree": "first_instance", "law": "civil", "result": "for", "pronounced_in_presence": True,
                 "amount_awarded": 64000000, "summary": "إلزام المدعى عليها بأداء قيمة الشحنة مع المصاريف."})

# 4. The claim's earlier twin, now on appeal: a trainee listed for the appeal court.
appealed = matter("civil_lawsuit", rafidain, lawyer, "استئناف حكم فسخ عقد توريد حديد التسليح", appeal_karkh,
                  opponent=furat, value=310000000)
Stage.create({"task_id": appealed.id, "stage": "first_instance", "department_id": karkh.id, "case_number": "411/ب",
              "case_year": 2026, "date_filed": D(-240)})
first = Judgment.create({"task_id": appealed.id, "date": D(-40), "department_id": karkh.id,
                         "court_degree": "first_instance", "law": "civil", "result": "against",
                         "pronounced_in_presence": True, "notified_date": D(-36),
                         "summary": "رد دعوى الشركة وتحميلها المصاريف."})
window = first.deadline_ids[:1]
window.write({"state": "done", "date_done": D(-30)})
Stage.create({"task_id": appealed.id, "stage": "appeal", "department_id": appeal_karkh.id, "case_number": "96/س",
              "case_year": 2026, "date_filed": D(-30)})
session(appealed, D(4), trainee, time=10.0, purpose="مرافعة")
appealed.poa_id = poa_rafidain

# 5. Labour case: an outside lawyer attends by substitution, under a power of attorney that forbids it.
labour_case = matter("labour_case", nineveh, lawyer2, "دعوى عامل مفصول للمطالبة بالتعويض", labour, role="defendant",
                     opponent=worker, value=18000000)
Stage.create({"task_id": labour_case.id, "stage": "first_instance", "department_id": labour.id,
              "case_number": "77/عمل", "case_year": 2026, "date_filed": D(-45)})
labour_case.poa_id = Poa.create({"poa_type": "judicial", "principal_company_id": nineveh.id, "number": "8840",
                                 "notary_office": "كاتب عدل الرصافة", "date_issued": D(-100),
                                 "agent_user_ids": [(6, 0, [lawyer2.id])], "substitution_allowed": False})
session(labour_case, D(5), False, time=11.0, purpose="استماع شهود", substitute_partner_id=outside.id)

# 6. Criminal complaint: a felony judgment pronounced in our presence.
criminal = matter("criminal_complaint", tigris, lawyer, "شكوى خيانة أمانة ضد أمين المخزن السابق", felony,
                  role="complainant")
session(criminal, D(-6), lawyer, purpose="النطق بالحكم").write({"state": "held", "outcome": "judgment"})
Judgment.create({"task_id": criminal.id, "date": D(-6), "department_id": felony.id, "court_degree": "felony",
                 "law": "criminal", "result": "partial", "pronounced_in_presence": True,
                 "summary": "الحكم على المتهم بالحبس سنتين مع إلزامه بالتعويض."})

# 7. A disciplinary penalty on an employee of a group company: the grievance chain.
grievance_case = matter("administrative", nineveh, lawyer2, "تظلم من عقوبة التوبيخ المفروضة على مدير الحركة",
                        employees, role="complainant")
first_step = Deadline.create({"task_id": grievance_case.id, "rule_id": env.ref(f"{M}.ldm_rule_adm_1").id,
                              "date_start": D(-20)})
first_step.write({"state": "done", "date_done": D(-15)})

# 8. Execution file: the debtor has been served the execution notice.
enforcement = matter("execution", rafidain, lawyer, "تنفيذ حكم مستحقات مشروع جسر الشهداء", execution,
                     opponent=furat, value=95000000)
Stage.create({"task_id": enforcement.id, "stage": "execution", "department_id": execution.id,
              "execution_file_number": "3310/تنفيذ/2026", "notification_date": D(-3)})

# 9. Sessions over the next two weeks, for the calendar and the roll.
for offset, task, who, hour, purpose in [
        (3, claim, lawyer, 9.0, "تبادل اللوائح"), (3, supply, lawyer2, 10.5, "مرافعة"),
        (4, eviction, lawyer, 9.5, "مراجعة"), (6, supply, lawyer2, 9.0, "استماع شهود"),
        (7, criminal, lawyer, 12.0, "مراجعة"), (10, claim, lawyer, 9.0, "مرافعة"),
        (11, labour_case, lawyer2, 10.0, "مرافعة"), (12, eviction, None, 9.0, "مرافعة"),
        (13, appealed, lawyer, 10.0, "تدقيق")]:
    session(task, D(offset), who, time=hour, purpose=purpose)

# 10. An old reply deadline nobody met, so the daily run reports it.
Deadline.create({"task_id": claim.id, "name": "الرد على لائحة المدعى عليها", "date_safe": D(-5),
                 "user_id": lawyer.id})
Deadline._cron_ldm_deadlines()
env.cr.commit()
print("litigation data ready:", Task.search_count([]), "matters,", Hearing.search_count([]), "sessions,",
      Deadline.search_count([]), "deadlines")
print("ids: claim", claim.id, "eviction", eviction.id, "supply", supply.id, "appealed", appealed.id,
      "labour", labour_case.id, "today_session", today_session.id)
