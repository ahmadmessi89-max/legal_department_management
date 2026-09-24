# One realistic Iraqi data set for the demo instance and the verification round.
#
# Run in `odoo-bin shell` from the workspace root, on a fresh database with the
# module installed and nothing else seeded:
#   odoo-bin shell -c odoo19_ldm.conf -d ldm_pro --no-http < docs/ldm/tools/seed_all.py
#
# It runs the five stream seeds unchanged (government first, because it loads the
# Iraqi reference library the others then reuse), with three seed-only shims:
#   * every stream login maps to one team of canonical users (login = password,
#     Arabic, Baghdad time), so a demo user sees the whole story on My Day;
#   * a ministry, body or client that already exists under the same normalised
#     name is reused instead of created a second time;
#   * the files the stream seeds write for their own screenshots go to a
#     scratch folder, not into docs/ldm/evidence.
# Then it switches every feature on under the hybrid preset (a group legal
# department that also bills its companies), so every screen has something on it.
# Local databases only: it sets passwords.
import os
import tempfile
import traceback

from odoo import api
from odoo.addons.legal_department_management.models.ldm_text import normalize

M = "legal_department_management"
TOOLS = os.path.join(os.getcwd(), "docs", "ldm", "tools")
STREAMS = ["seed_gov.py", "seed_lit.py", "seed_ws.py", "seed_money.py", "seed_reg.py"]

# login: (name, role group, extra values)
TEAM = {
    "manager": ("المستشار سعد الربيعي", "group_legal_manager",
                {"ldm_licence_class": "unrestricted", "ldm_bar_number": "4127"}),
    "lawyer": ("المحامية زينب الجبوري", "group_legal_user", {"ldm_licence_class": "a", "ldm_bar_number": "18852"}),
    "lawyer2": ("المحامي علي الساعدي", "group_legal_user", {"ldm_licence_class": "b", "ldm_bar_number": "21410"}),
    "trainee": ("المحامية المتمرنة نور علي", "group_legal_user",
                {"ldm_licence_class": "trainee", "ldm_bar_number": "T-3319"}),
    "clerk": ("حيدر عبد الأمير", "group_ldm_clerk", {}),
    "approver": ("د. حسين كاظم", "group_ldm_approver", {}),
    "auditor": ("نور الهدى السامرائي", "group_ldm_auditor", {}),
    "billing": ("مريم الحسني", "group_ldm_billing_user", {}),
    "employee": ("سارة محمود", None, {}),
}
LOGINS = {
    "gov_clerk": "clerk", "gov_lawyer": "lawyer", "gov_manager": "manager", "gov_auditor": "auditor",
    "lit_manager": "manager", "lit_lawyer": "lawyer", "lit_lawyer2": "lawyer2", "lit_trainee": "trainee",
    "lit_clerk": "clerk", "lit_auditor": "auditor",
    "zainab": "lawyer", "ali": "clerk", "hussein": "approver", "sara": "manager", "mustafa": "auditor",
    "karim": "lawyer2",
    "money_lawyer": "lawyer", "money_lawyer2": "lawyer2", "money_clerk": "clerk", "money_billing": "billing",
    "money_manager": "manager",
    "reg_clerk": "clerk", "reg_lawyer": "lawyer", "reg_lawyer2": "lawyer2", "reg_approver": "approver",
    "reg_manager": "manager", "reg_auditor": "auditor", "reg_employee": "employee",
}

Users = env["res.users"].with_context(no_reset_password=True, active_test=False)
if Users.search([("login", "=", "billing")]):
    raise SystemExit("seed_all already ran on this database")

# 1. The team.
base_user = env.ref("base.group_user")
for login, (name, role, extra) in TEAM.items():
    groups = [base_user.id] + ([env.ref(f"{M}.{role}").id] if role else [])
    values = dict(extra, name=name, login=login, password=login, lang="ar_001", tz="Asia/Baghdad",
                  email=f"{login}@sumer-legal.iq", group_ids=[(6, 0, groups)])
    if "odoobot_state" in Users._fields:
        values["odoobot_state"] = "disabled"
    Users.create(values)
env.cr.commit()

# 2. Seed-only shims.
UsersClass = type(env["res.users"])
MinistryClass = type(env["legal.ministry"])
DepartmentClass = type(env["legal.department"])
CompanyClass = type(env["legal.company"])
originals = {cls: cls.create for cls in (UsersClass, MinistryClass, DepartmentClass, CompanyClass)}


def merged_values(record, vals):
    """What a second seed adds to a record the first seed made: its people join
    the teams (a (6, 0, ids) becomes links), and it fills only empty fields."""
    out = {}
    for key, value in vals.items():
        field = record._fields.get(key)
        if not field or key == "name":
            continue
        if field.type in ("many2many", "one2many"):
            links = []
            for command in value or []:
                if command[0] == 6:
                    links += [(4, rid) for rid in command[2]]
                elif command[0] == 4 or field.type == "one2many":
                    links.append(command)
            if links:
                out[key] = links
        elif not record[key]:
            out[key] = value
    return out


def reuse_or_create(cls, match):
    create = originals[cls]

    @api.model_create_multi
    def shim(self, vals_list):
        result = self.browse()
        for vals in vals_list:
            found = match(self, vals)
            if found:
                if cls is UsersClass:
                    found.write({k: v for k, v in vals.items() if k not in ("login", "password", "name", "email")})
                else:
                    found.write(merged_values(found, vals))
                result |= found
            else:
                result |= create(self, [vals])
        return result
    cls.create = shim


def match_user(model, vals):
    login = LOGINS.get(vals.get("login"), vals.get("login"))
    return model.with_context(active_test=False).search([("login", "=", login)], limit=1)


def match_by_name(extra_domain):
    def match(model, vals):
        key = normalize(vals.get("name") or "")
        if not key:
            return model.browse()
        domain = extra_domain(vals)
        return model.with_context(active_test=False).search(domain).filtered(
            lambda record: normalize(record.name) == key)[:1]
    return match


reuse_or_create(UsersClass, match_user)
reuse_or_create(MinistryClass, match_by_name(lambda vals: []))
reuse_or_create(DepartmentClass, match_by_name(lambda vals: [("ministry_id", "=", vals.get("ministry_id") or False)]))
reuse_or_create(CompanyClass, match_by_name(lambda vals: []))

# 3. The five stream seeds, unchanged, each in its own namespace.
workspace = os.getcwd()
scratch = tempfile.mkdtemp(prefix="ldm_seed_")
try:
    for script in STREAMS:
        path = os.path.join(TOOLS, script)
        source = open(path, encoding="utf-8").read()
        os.chdir(scratch)  # the stream seeds write their capture lists relative to the working folder
        print(f"--- {script}")
        try:
            # in the team's language, as the daily jobs run: generated names are stored text
            seed_env = env(context=dict(env.context, lang="ar_001", tz="Asia/Baghdad"))
            exec(compile(source, path, "exec"), {"env": seed_env, "__name__": "__main__", "__file__": path})
        except SystemExit as stop:
            print(f"{script} stopped: {stop}")
        except Exception:
            traceback.print_exc()
            env.cr.rollback()
            raise
        finally:
            os.chdir(workspace)
        env.cr.commit()
finally:
    for cls, create in originals.items():
        cls.create = create

# 4. Every feature on, under the hybrid preset, and the team's own names back.
settings = env["res.config.settings"]
settings._ldm_apply_preset("hybrid")
from odoo.addons.legal_department_management.models.res_config_settings import LDM_SWITCHES  # noqa: E402

employee_group = env.ref("base.group_user").sudo()
for switch in LDM_SWITCHES:
    employee_group._apply_group(env.ref(f"{M}.{switch}").sudo())
env.company.write({"name": "مجموعة سومر القابضة — القسم القانوني",
                   "ldm_calendar_id": env.ref(f"{M}.ldm_calendar_iraq").id})
# A plain wordmark for the fictional group, so the letterhead does not print
# Odoo's "Your logo" placeholder (docs/ldm/tools/demo_logo.png, demo data only).
logo_path = os.path.join(TOOLS, "demo_logo.png")
if os.path.exists(logo_path):
    import base64  # noqa: E402

    env.company.logo = base64.b64encode(open(logo_path, "rb").read())
for login, (name, role, extra) in TEAM.items():
    Users.search([("login", "=", login)]).write({"name": name})
# The administrator appears in chatters and "created by" columns: an English
# "Administrator" is the one Latin word left on an Arabic screen.
env.ref("base.user_admin").write({"name": "مدير النظام", "lang": "ar_001", "tz": "Asia/Baghdad"})
env["legal.task"]._ldm_run_reminders()
env.cr.commit()

Task = env["legal.task"]
print("seed_all ready:", Task.search_count([]), "matters,", env["legal.company"].search_count([]), "clients,",
      env["legal.hearing"].search_count([]), "sessions,", env["legal.deadline"].search_count([]), "deadlines")
print("logins (password = login):", ", ".join(TEAM))
