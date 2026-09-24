# Run in `odoo-bin shell` (stream G, database ldm_g) with the module installed:
#   odoo-bin shell -c odoo19_ldm_gov.conf -d ldm_g < docs/ldm/tools/seed_gov.py
# Realistic Iraqi data for the government screens: the reference library, three
# group companies with their document vaults and obligations, government
# transactions at several stages with counter visits, and one local user per role
# (login = password, Arabic, Asia/Baghdad). Safe to run twice: it looks before it
# creates. Local instance only: it sets passwords.
import base64
import datetime as dt

today = dt.date.today()
M = "legal_department_management"
Users = env["res.users"].with_context(no_reset_password=True)

# A small receipt photo for the visits and the vault (a 1x1 PNG). Phone numbers
# are written without spaces and file names in Latin letters: a run of digits
# separated by spaces is reordered by the right-to-left layout.
PNG = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def user(login, name, group):
    existing = Users.search([("login", "=", login)])
    values = {"name": name, "lang": "ar_001", "tz": "Asia/Baghdad",
              "group_ids": [(6, 0, [env.ref("base.group_user").id, env.ref(f"{M}.{group}").id])]}
    if "odoobot_state" in Users._fields:
        # No onboarding chat: on a phone it opens over the screen being captured.
        values["odoobot_state"] = "disabled"
    if existing:
        existing.write(values)
        return existing
    return Users.create(dict(values, login=login, password=login))


clerk = user("gov_clerk", "حيدر عبد الأمير", "group_ldm_clerk")
lawyer = user("gov_lawyer", "زينب كاظم", "group_legal_user")
manager = user("gov_manager", "علي الربيعي", "group_legal_manager")
auditor = user("gov_auditor", "سارة جواد", "group_ldm_auditor")
admin = env.ref("base.user_admin")
admin.write({"lang": "ar_001", "tz": "Asia/Baghdad",
             "group_ids": [(4, env.ref(f"{M}.group_legal_manager").id)]})

# The Iraqi reference library (idempotent).
report = env["legal.reference.library"].ldm_load()
print("library:", report)

Department = env["legal.department"]
Template = env["legal.task.template"]
DocType = env["legal.document.type"]


def body(code):
    return Department.search([("code", "=", code)], limit=1)


def service(code):
    return Template.search([("ldm_ref_code", "=", code)], limit=1)


def doctype(code):
    return DocType.search([("code", "=", code)], limit=1)


tax = body("IQ-MOF-GCT")
registrar = body("IQ-MOT-REG")
chamber = body("IQ-FICC-BGW")
if not tax.contact_ids:
    tax.write({
        "phone": "07901234560",
        "location_url": "https://maps.google.com/?q=33.3152,44.3661",
        "notes": "قسم الشركات في الطابق الثاني. يطلب الموظف نسخة ملونة من البطاقة الضريبية.",
        "contact_ids": [(0, 0, {"name": "أبو محمد", "role": "شباك الشركات", "phone": "07701112233",
                                "notes": "يفضل المراجعة قبل الحادية عشرة"}),
                        (0, 0, {"name": "م. سلمى حسين", "role": "قسم التدقيق", "phone": "07809445566"})],
    })
if not registrar.contact_ids:
    registrar.write({"phone": "07901555120",
                     "contact_ids": [(0, 0, {"name": "أبو علي", "role": "شعبة التصديق", "phone": "07711998877"})]})

Company = env["legal.company"]


def client(name, **values):
    existing = Company.search([("name", "=", name)], limit=1)
    if existing:
        return existing
    values.setdefault("lawyer_id", lawyer.id)
    values.setdefault("lawyer_ids", [(6, 0, [lawyer.id])])
    return Company.create(dict(values, name=name))


rafidain = client("شركة الرافدين للمقاولات العامة", registration_number="م.ش/2011/4521", tax_number="100452117",
                  owner_name="عمار الجبوري", phone="07701234567", chamber_number="11873", chamber_grade="ممتاز")
dijla = client("شركة دجلة للنقل والتخليص الكمركي", registration_number="م.ش/2015/7780", tax_number="100778021",
               owner_name="نور الهدى السامرائي")
furat = client("شركة الفرات للتجارة العامة", registration_number="م.ش/2009/3311", tax_number="100331190",
               owner_name="حسن العبيدي")

Vault = env["legal.company.document"]


def vault(company, code, number, issued, expiry, with_file=True):
    doc_type = doctype(code)
    existing = Vault.search([("legal_company_id", "=", company.id), ("document_type_id", "=", doc_type.id),
                             ("number", "=", number)], limit=1)
    if existing:
        return existing
    values = {"legal_company_id": company.id, "document_type_id": doc_type.id, "number": number,
              "date_issued": issued, "date_expiry": expiry}
    if with_file:
        values.update({"file_name": f"{code}.png", "file_data": PNG})
    return Vault.create(values)


d = dt.timedelta
vault(rafidain, "incorporation_certificate", "م.ش/2011/4521", dt.date(2011, 3, 14), False)
vault(rafidain, "tax_card", "ض/100452117", today - d(days=160), today + d(days=205))
vault(rafidain, "tax_clearance", "ب.ذ/2026/3390", today - d(days=345), today + d(days=20))
vault(rafidain, "chamber_id", "غ.ت/11873", today - d(days=375), today - d(days=10))
vault(rafidain, "runner_authorisation", "خ/2026/77", today - d(days=40), today + d(days=325))
vault(rafidain, "final_accounts", "ح.خ/2025", today - d(days=120), False)
vault(dijla, "incorporation_certificate", "م.ش/2015/7780", dt.date(2015, 6, 2), False)
vault(dijla, "chamber_id", "غ.ت/20441", today - d(days=300), today + d(days=65))
vault(furat, "tax_clearance", "ب.ذ/2026/1180", today - d(days=100), today + d(days=265))

Obligation = env["legal.obligation"]


def obligation(company, name, code, recurrence, month, day, lead):
    existing = Obligation.search([("legal_company_id", "=", company.id), ("name", "=", name)], limit=1)
    if existing:
        return existing
    return Obligation.create({"legal_company_id": company.id, "name": name, "template_id": service(code).id,
                              "recurrence": recurrence, "month": month, "day": day, "lead_days": lead})


obligation(rafidain, "الإقرار الضريبي السنوي", "SVC-TAX-B", "yearly", 5, 31, 60)
obligation(rafidain, "اشتراكات الضمان الاجتماعي", "SVC-SS-A", "monthly", 1, 15, 7)
obligation(rafidain, "تجديد هوية غرفة التجارة", "SVC-CHM-A", "yearly", 11, 1, 30)
obligation(dijla, "تجديد هوية شركة النقل", "SVC-TRN-A", "yearly", 1, 15, 21)
obligation(furat, "الحسابات الختامية لدى المسجل", "SVC-REG-B", "yearly", 7, 31, 45)

Task = env["legal.task"]


def matter(company, code, title, **values):
    existing = Task.search([("legal_company_id", "=", company.id), ("name", "=", title)], limit=1)
    if existing:
        return existing, False
    task = Task.browse(Task.with_user(lawyer).create_from_template(
        dict(values, template_id=service(code).id, legal_company_id=company.id, name=title)))
    task.with_user(lawyer).write({"lawyer_ids": [(4, clerk.id)]})
    return task, True


def log_visit(task, **values):
    step = task.step_ids.filtered(lambda s: s.is_visit and s.state == "todo").sorted("sequence")[:1]
    action = step.with_user(clerk).action_ldm_log_visit()
    Wizard = env["legal.visit.wizard"].with_user(clerk).with_context(action["context"])
    defaults = Wizard.default_get(list(Wizard._fields))
    defaults.update(values)
    Wizard.create(defaults).action_confirm()
    return step


# 1. Tax clearance for Rafidain: documents gathered, file at the body for 12
#    working days (the body usually answers in 15), second visit still pending.
clearance, new = matter(rafidain, "SVC-TAX-C", "براءة ذمة ضريبية لسنة 2026 — مناقصة وزارة الإعمار")
if new:
    for doc in clearance.document_ids:
        if doc.state == "missing":
            doc.write({"state": "received", "file_name": f"{doc.document_type_id.code}.png", "file_data": PNG})
    clearance.step_ids.filtered(lambda s: not s.is_visit).write({"state": "done", "done_date": today - d(days=19)})
    log_visit(clearance, fee_amount=25000, receipt_number="و/2026/88412", photo=PNG, photo_name="receipt.png",
              visit_date=today - d(days=17))
    clearance.write({"date_submitted": today - d(days=17), "waiting_on": "body"})
    log_visit(clearance, result="pending", next_date=today + d(days=2),
              waiting_for="تأييد مسجل الشركات بآخر تعديل على رأس المال")

# 2. Chamber ID renewal for Dijla: one paper waits for the issuing body's confirmation.
renewal, new = matter(dijla, "SVC-CHM-A", "تجديد هوية غرفة تجارة بغداد لشركة دجلة")
if new:
    auth = renewal.document_ids.filtered(lambda doc: doc.document_type_id.code == "runner_authorisation")
    auth.write({"state": "received", "file_name": "authorisation.png", "file_data": PNG})
    auth.action_ldm_request_verification()

# 3. Final accounts at the registrar for Furat: done this year (coverage shows it).
accounts, new = matter(furat, "SVC-REG-B", "إيداع الحسابات الختامية لسنة 2025 لدى مسجل الشركات")
if new:
    accounts.step_ids.write({"state": "done", "done_date": today - d(days=30)})
    accounts.document_ids.write({"state": "received"})
    accounts._ldm_close("completed", "")

# 4. Annual vehicle registration for Rafidain: just opened, first visit tomorrow.
matter(rafidain, "SVC-TRF-A", "تجديد سنوية سيارة الشركة (بيك أب تويوتا)")

# 5. Import licence for Dijla: submitted 25 working days ago, past the body's usual time.
licence, new = matter(dijla, "SVC-CHM-B", "إجازة استيراد معدات مخزنية")
if new:
    log_visit(licence, fee_amount=50000, receipt_number="و/2026/51207", visit_date=today - d(days=36))
    licence.write({"date_submitted": today - d(days=36), "waiting_on": "body"})

# Track the yearly services for coverage (the library already marks them).
env["legal.company.document"]._cron_ldm_vault_deadlines()
env["legal.task"]._ldm_run_reminders()
env.cr.commit()
print("gov seed ready:", Task.search_count([("kind", "=", "government")]), "government matters;",
      Vault.search_count([]), "company documents;", Obligation.search_count([]), "obligations")
for record in (clearance, renewal, accounts, licence):
    print(record.id, record.task_number, record.name)
print("users:", clerk.id, lawyer.id, manager.id, auditor.id)
print("bodies: tax", tax.id, "registrar", registrar.id, "karkh court", body("IQ-SJC-FI-KRK").id)
print("clients:", rafidain.id, dijla.id, furat.id)
