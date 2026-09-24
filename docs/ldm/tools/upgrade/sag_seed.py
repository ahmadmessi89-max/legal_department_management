# Run in `odoo-bin shell` with the ORIGINAL 19.0.6.3.0 module (commit ccebae7) on a
# copy of ldm_baseline. Builds SAG-shaped data: the situations the upgrade must
# survive (courts under the Supreme Judicial Council, lawsuits and government
# transactions with one session date, expenses as a float, the hidden lawyer_id
# grant, duplicated cron reminders, a ministry that disagrees with its department,
# a duplicated matter number). Uses `env` from the shell.
import datetime as dt

today = dt.date.today()
Users = env["res.users"].with_context(no_reset_password=True)
g_user = env.ref("legal_department_management.group_legal_user")
g_manager = env.ref("legal_department_management.group_legal_manager")
base_user = env.ref("base.group_user")


def user(login, name, groups):
    existing = Users.search([("login", "=", login)])
    if existing:
        return existing
    return Users.create({"login": login, "name": name, "password": login + "123",
                         "group_ids": [(6, 0, [base_user.id] + [g.id for g in groups])]})


lawyer1 = user("sag_lawyer1", "Zainab Lawyer", [g_user])
lawyer2 = user("sag_lawyer2", "Omar Lawyer", [g_user])
manager = user("sag_manager", "Legal Manager", [g_manager])

Ministry = env["legal.ministry"]
Department = env["legal.department"]
council = Ministry.search([("name", "=", "مجلس القضاء الأعلى")], limit=1)
trade = Ministry.search([("name", "=", "وزارة التجارة")], limit=1)
finance = Ministry.search([("name", "=", "وزارة المالية")], limit=1)
karkh = Department.search([("name", "=", "محكمة بداءة الكرخ")], limit=1)
appeal = Department.search([("name", "=", "محكمة استئناف بغداد")], limit=1)
registry = Department.search([("name", "=", "دائرة تسجيل الشركات")], limit=1)
tax = Department.search([("name", "=", "الهيئة العامة للضرائب")], limit=1)
labour = Department.create({"name": "محكمة العمل في بغداد", "ministry_id": council.id})
notary = Department.create({"name": "كاتب عدل الكرادة", "ministry_id": env["legal.ministry"].create({"name": "وزارة العدل"}).id})

Company = env["legal.company"]
rafidain = Company.search([("name", "=", "شركة الرافدين للمقاولات")], limit=1)
tigris = Company.search([("name", "=", "مجموعة دجلة التجارية")], limit=1)
rafidain.write({"lawyer_ids": [(6, 0, [lawyer1.id])], "lawyer_id": lawyer1.id, "phone": "07701234567",
                "email": "legal@rafidain.example", "address": "بغداد - الكرادة\nشارع 62", "tax_number": "T-1001",
                "registration_number": "R-2001"})
tigris.write({"lawyer_ids": [(6, 0, [lawyer2.id])], "lawyer_id": lawyer2.id, "phone": "07809876543"})
# The hidden grant: lawyer2 created a client for lawyer1 and keeps access through lawyer_id only.
furat = Company.with_user(lawyer2).create({"name": "شركة الفرات للنقل", "lawyer_ids": [(6, 0, [lawyer1.id])]})

Task = env["legal.task"]
# Existing baseline matters: assign lawyers
for task in Task.search([]):
    lawyer = task.legal_company_id.lawyer_id or lawyer1
    task.write({"lawyer_ids": [(6, 0, [lawyer.id])], "lawyer_id": lawyer.id})
suit = Task.create({"name": "دعوى عمالية ضد عامل سابق", "legal_company_id": tigris.id, "department_id": labour.id,
                    "ministry_id": council.id, "state": "in_progress", "session_date": str(today + dt.timedelta(days=6)),
                    "lawyer_ids": [(6, 0, [lawyer2.id])], "lawyer_id": lawyer2.id, "expenses_amount": 75000})
poa = Task.create({"name": "وكالة خاصة لدى كاتب العدل", "legal_company_id": furat.id, "department_id": notary.id,
                   "state": "in_progress", "session_date": str(today - dt.timedelta(days=4)),
                   "lawyer_ids": [(6, 0, [lawyer1.id])], "lawyer_id": lawyer2.id})
# A ministry that disagrees with its department
wrong = Task.create({"name": "تجديد هوية غرفة التجارة", "legal_company_id": rafidain.id, "department_id": registry.id,
                     "ministry_id": finance.id, "state": "draft", "lawyer_ids": [(6, 0, [lawyer1.id])],
                     "lawyer_id": lawyer1.id})
# A duplicated matter number (the showcase's fallback)
env.cr.execute("UPDATE legal_task SET task_number = %s WHERE id = %s", (suit.task_number, wrong.id))
# Duplicated cron reminders (SAG's cron adds one every day)
todo = env.ref("mail.mail_activity_data_todo")
for _i in range(3):
    env["mail.activity"].create({"res_model_id": env["ir.model"]._get_id("legal.task"), "res_id": suit.id,
                                 "activity_type_id": todo.id, "user_id": lawyer2.id,
                                 "summary": "تنبيه استحقاق متأخر: " + suit.name,
                                 "date_deadline": str(today - dt.timedelta(days=1))})
# An approval in flight
suit.write({"approval_state": "to_approve"})
env.cr.commit()
print("SAG-shaped data seeded:", Task.search_count([]), "matters,", Company.search_count([]), "clients")
