"""Generate security/ir.model.access.csv (foundation) and empty per-stream ACL files."""
import os
_here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
os.chdir(_here if os.path.exists(os.path.join(_here, "__manifest__.py"))
         else os.path.join(_here, "custom_addons", "legal_department_management"))
rows = []
G = {
    'clerk': 'group_ldm_clerk', 'lawyer': 'group_legal_user', 'manager': 'group_legal_manager',
    'billing': 'group_ldm_billing_user', 'auditor': 'group_ldm_auditor', 'req': 'group_ldm_requests',
}


def add(xid, model, group, perms):
    r, w, c, d = [int(ch != '-') for ch in perms]
    rows.append(f"{xid},{model.replace('_', '.')},model_{model},{G[group]},{r},{w},{c},{d}")


# SAG's original ids first, values per SPEC 3.3 and 14.2
add('access_legal_ministry_user', 'legal_ministry', 'lawyer', 'RWC-')
add('access_legal_ministry_manager', 'legal_ministry', 'manager', 'RWCD')
add('access_legal_department_user', 'legal_department', 'lawyer', 'RWC-')
add('access_legal_department_manager', 'legal_department', 'manager', 'RWCD')
add('access_legal_company_user', 'legal_company', 'lawyer', 'RWC-')
add('access_legal_company_manager', 'legal_company', 'manager', 'RWCD')
add('access_legal_task_user', 'legal_task', 'lawyer', 'RWC-')
add('access_legal_task_manager', 'legal_task', 'manager', 'RWCD')
add('access_legal_task_wizard_user', 'legal_task_create_wizard', 'clerk', 'RWC-')
add('access_legal_company_report_wizard_user', 'legal_company_report_wizard', 'clerk', 'RWC-')
add('access_legal_general_report_wizard_user', 'legal_general_report_wizard', 'clerk', 'RWC-')
READ = 'R---'
spec = {
    'legal_task': {'clerk': 'RWC-', 'billing': READ, 'auditor': READ},
    'legal_company': {'clerk': READ, 'billing': READ, 'auditor': READ},
    'legal_ministry': {'clerk': READ, 'billing': READ, 'auditor': READ},
    'legal_department': {'clerk': READ, 'billing': READ, 'auditor': READ},
    'legal_department_contact': {'clerk': READ, 'lawyer': 'RWCD', 'manager': 'RWCD', 'auditor': READ},
    'legal_task_template': {'clerk': READ, 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_task_template_step': {'clerk': READ, 'manager': 'RWCD', 'auditor': READ},
    'legal_task_template_document': {'clerk': READ, 'manager': 'RWCD', 'auditor': READ},
    'legal_document_type': {'clerk': READ, 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_task_step': {'clerk': 'RWC-', 'lawyer': 'RWCD', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_task_document': {'clerk': 'RWC-', 'lawyer': 'RWCD', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_hearing': {'clerk': 'RWC-', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_court_stage': {'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_task_party': {'clerk': READ, 'lawyer': 'RWCD', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_judgment': {'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_appeal_rule': {'clerk': READ, 'manager': 'RWCD', 'auditor': READ},
    'legal_deadline': {'clerk': 'RW--', 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_holiday': {'clerk': READ, 'manager': 'RWCD', 'auditor': READ},
    'legal_poa': {'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_letter_template': {'clerk': READ, 'manager': 'RWCD', 'auditor': READ},
    'legal_correspondence': {'clerk': 'RWC-', 'manager': 'RWCD', 'auditor': READ},
    'legal_request': {'req': 'RWC-', 'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'auditor': READ},
    'legal_company_document': {'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_obligation': {'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'auditor': READ},
    'legal_guarantee': {'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_expense_category': {'clerk': READ, 'manager': 'RWCD', 'billing': READ, 'auditor': READ},
    'legal_task_expense': {'clerk': 'RWC-', 'manager': 'RWCD', 'billing': 'RWC-', 'auditor': READ},
    'legal_client_fund_line': {'clerk': 'R-C-', 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': 'RWCD', 'auditor': READ},
    'legal_advance': {'clerk': 'RWC-', 'manager': 'RWCD', 'billing': 'RWCD', 'auditor': READ},
    'legal_engagement': {'clerk': READ, 'lawyer': 'RWC-', 'manager': 'RWCD', 'billing': 'RWCD', 'auditor': READ},
    'legal_engagement_line': {'clerk': READ, 'lawyer': 'RWCD', 'manager': 'RWCD', 'billing': 'RWCD', 'auditor': READ},
    'legal_time_entry': {'clerk': 'RWC-', 'lawyer': 'RWCD', 'manager': 'RWCD', 'billing': 'RWCD', 'auditor': READ},
    'legal_conflict_check': {'clerk': 'R-C-', 'lawyer': 'R-C-', 'manager': 'RWC-', 'auditor': READ},
    'legal_task_decision_wizard': {'clerk': 'RWC-'},
    'legal_company_report_wizard': {'auditor': 'RWC-', 'billing': 'RWC-'},
    'legal_general_report_wizard': {'auditor': 'RWC-', 'billing': 'RWC-'},
}
for model, perms in spec.items():
    for role, p in perms.items():
        add(f"access_{model}_{role}", model, role, p)
HEADER = "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
with open('security/ir.model.access.csv', 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(HEADER + "\n".join(rows) + "\n")
for stream in ('gov', 'lit', 'ws', 'money', 'reg'):
    path = f'security/ir.model.access-{stream}.csv'
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(HEADER)
print(len(rows), 'foundation ACL rows')
