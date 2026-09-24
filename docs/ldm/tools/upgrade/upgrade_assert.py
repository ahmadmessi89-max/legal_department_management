# Run in `odoo-bin shell` with the NEW module after `-u legal_department_management`
# on the SAG-shaped copy. Compares with the pre-upgrade snapshot (env LDM_BEFORE)
# and checks every migration step. Prints PASS/FAIL lines and exits non-zero on failure.
import json
import os
import sys

before = json.load(open(os.environ["LDM_BEFORE"], encoding="utf-8"))
failures = []


def check(label, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + label + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        failures.append(label)


Task = env["legal.task"].sudo().with_context(active_test=False)
Company = env["legal.company"].sudo().with_context(active_test=False)

# Counts unchanged
for model, count in before["counts"].items():
    now = env[model].sudo().with_context(active_test=False).search_count([])
    check(f"{model} count unchanged ({count})", now == count, f"now {now}")

# Visibility: every user sees at least what they saw before (M3 keeps the hidden
# grant visible; M11 keeps admins' access). Nobody loses a matter or a client.
for login, entry in before["users"].items():
    user = env["res.users"].search([("login", "=", login)])
    if not user:
        continue
    for model in ("legal.task", "legal.company"):
        was = entry.get(model)
        if isinstance(was, str):
            continue
        now = env[model].with_user(user).search([]).ids
        lost = sorted(set(was) - set(now))
        check(f"{login} keeps every {model} they saw", not lost, f"lost {lost}")

# M11: admins are explicit legal managers; Settings no longer implies it
manager = env.ref("legal_department_management.group_legal_manager")
check("base.group_system no longer implies legal manager",
      manager not in env.ref("base.group_system").all_implied_ids)
admin = env.ref("base.user_admin")
check("admin is still a legal manager (explicitly)", manager in admin.all_group_ids)

# Courts classified before kinds and sessions
karkh = env["legal.department"].search([("name", "=", "محكمة بداءة الكرخ")], limit=1)
check("Karkh first-instance court classified", karkh.body_kind == "court" and karkh.court_degree == "first_instance",
      f"{karkh.body_kind}/{karkh.court_degree}")
labour = env["legal.department"].search([("name", "=", "محكمة العمل في بغداد")], limit=1)
check("labour court classified", labour.court_degree == "labour", labour.court_degree)
registry = env["legal.department"].search([("name", "=", "دائرة تسجيل الشركات")], limit=1)
check("registry stays a government body", registry.body_kind == "government", registry.body_kind)

# Kinds and sessions
for task in Task.search([]):
    if task.department_id.body_kind == "court":
        check(f"{task.task_number} at a court is a lawsuit", task.kind == "litigation", task.kind)
    elif task.department_id:
        check(f"{task.task_number} at a body is a government transaction", task.kind == "government", task.kind)
suit = Task.search([("name", "=", "دعوى مطالبة بمبلغ عقد توريد")], limit=1)
check("Karkh lawsuit has exactly one session", len(suit.hearing_ids) == 1, len(suit.hearing_ids))
check("its session date survives as the next session", suit.session_date == suit.hearing_ids[:1].date)
poa = Task.search([("name", "=", "وكالة خاصة لدى كاتب العدل")], limit=1)
check("notary session became a done visit step", len(poa.step_ids.filtered("is_visit")) == 1
      and poa.step_ids.filtered("is_visit").state == "done")

# Expenses
labour_suit = Task.search([("name", "=", "دعوى عمالية ضد عامل سابق")], limit=1)
check("legacy expenses became one expense line", len(labour_suit.expense_ids) == 1
      and labour_suit.expenses_amount == 75000, f"{len(labour_suit.expense_ids)} / {labour_suit.expenses_amount}")

# Partners
rafidain = Company.search([("name", "=", "شركة الرافدين للمقاولات")], limit=1)
check("every client has a contact", not Company.search([("partner_id", "=", False)]))
check("client phone carried to the contact", rafidain.partner_id.phone == "07701234567", rafidain.partner_id.phone)
check("client email carried to the contact", rafidain.email == "legal@rafidain.example", rafidain.email)
check("client tax number on the contact", rafidain.partner_id.vat == "T-1001", rafidain.partner_id.vat)

# M3: responsible in team
check("every responsible is on the team", not Task.search([]).filtered(lambda t: t.lawyer_id and t.lawyer_id not in t.lawyer_ids))

# M4: ministry follows department
wrong = Task.search([("name", "=", "تجديد هوية غرفة التجارة")], limit=1)
check("ministry repaired from the department", wrong.ministry_id == wrong.department_id.ministry_id)

# Unique numbers
numbers = Task.search([]).mapped("task_number")
check("matter numbers are unique", len(numbers) == len(set(numbers)))

# M9: duplicated reminders removed
labour_activities = labour_suit.activity_ids.filtered(lambda a: "تنبيه" in (a.summary or ""))
check("duplicated cron reminders reduced to one", len(labour_activities) == 1, len(labour_activities))

# Approval in flight preserved
check("approval in flight preserved", labour_suit.approval_state == "to_approve", labour_suit.approval_state)

# M14 hybrid preset
params = env["ir.config_parameter"].sudo()
check("hybrid preset applied", params.get_param("legal_department_management.preset") == "hybrid")
check("billing switch on (hybrid)",
      env.ref("legal_department_management.group_ldm_billing") in env.ref("base.group_user").all_implied_ids)
check("legal calendar set", bool(env.company.ldm_calendar_id))

# The cron still calls the kept method and runs
cron = env.ref("legal_department_management.ir_cron_legal_task_checker")
check("cron still calls the kept method", "_cron_check_upcoming_sessions" in cron.code)
Task.env["legal.task"]._cron_check_upcoming_sessions()
check("cron runs after the upgrade", True)

print(f"{len(failures)} failure(s)")
env.cr.rollback()
sys.exit(1 if failures else 0)
