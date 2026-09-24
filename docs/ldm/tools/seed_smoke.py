# Run in `odoo-bin shell` on a fresh database with the module installed:
# a handful of records so every foundation screen has something on it.
import datetime as dt

today = dt.date.today()
env["res.users"].browse(2).write({"lang": "ar_001", "tz": "Asia/Baghdad"})
admin = env.ref("base.user_admin")
admin.group_ids = [(4, env.ref("legal_department_management.group_legal_manager").id)]
Ministry, Department = env["legal.ministry"], env["legal.department"]
council = Ministry.create({"name": "مجلس القضاء الأعلى", "body_kind": "judicial"})
trade = Ministry.create({"name": "وزارة التجارة"})
karkh = Department.create({"name": "محكمة بداءة الكرخ", "ministry_id": council.id, "body_kind": "court",
                           "court_degree": "first_instance"})
registry = Department.create({"name": "دائرة تسجيل الشركات", "ministry_id": trade.id})
Company = env["legal.company"]
rafidain = Company.create({"name": "شركة الرافدين للمقاولات", "phone": "07701234567", "registration_number": "R-2001"})
tigris = Company.create({"name": "مجموعة دجلة التجارية"})
Task = env["legal.task"]
gov = env.ref("legal_department_management.ldm_template_government")
suit = env.ref("legal_department_management.ldm_template_civil_lawsuit")
Task.create_from_template({"template_id": gov.id, "legal_company_id": rafidain.id, "department_id": registry.id})
Task.create_from_template({"template_id": suit.id, "legal_company_id": tigris.id, "department_id": karkh.id,
                           "key_date": str(today + dt.timedelta(days=4)), "our_role": "plaintiff",
                           "opponent_name": "شركة الخصم التجارية"})
env.cr.commit()
print("smoke data ready:", Task.search_count([]), "matters")
