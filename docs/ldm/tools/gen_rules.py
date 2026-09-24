import os
_here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
os.chdir(_here if os.path.exists(os.path.join(_here, "__manifest__.py"))
         else os.path.join(_here, "custom_addons", "legal_department_management"))
ASSIGNED = ("['|', '|', '|', '|', ('{p}lawyer_id', '=', user.id), ('{p}lawyer_ids', 'in', [user.id]), "
            "'&', ('{p}confidential', '=', False), ('{p}legal_company_id.lawyer_ids', 'in', [user.id]), "
            "'&', ('{p}confidential', '=', False), ('{p}step_ids.user_id', '=', user.id), "
            "('{p}hearing_ids.attending_user_id', '=', user.id)]")
ALL = "[(1, '=', 1)]"
COMPANY = "['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]"
out = ['<?xml version="1.0" encoding="utf-8"?>', '<odoo>', '''    <!--
        Who sees which matter. Clerks and lawyers see the matters they are
        responsible for, on the team of, attend a session of, or hold a step
        of, plus every non-confidential matter of the clients they look after.
        Managers, auditors, billing and (when Settings says lawyers see every
        matter) everyone with legal access see all. The rule ids of 19.0.6.3.0
        are kept; their domains are rewritten.
    -->''']


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rule(xid, name, model, domain, groups=None, read=True, write=True, create=True, unlink=True):
    g = f'\n        <field name="groups" eval="[(4, ref(\'{groups}\'))]"/>' if groups else ''
    perms = ''.join(f'\n        <field name="perm_{k}" eval="{v}"/>' for k, v in
                    (('read', read), ('write', write), ('create', create), ('unlink', unlink)))
    out.append(f'''    <record id="{xid}" model="ir.rule">
        <field name="name">{name}</field>
        <field name="model_id" ref="model_{model}"/>
        <field name="domain_force">{esc(domain)}</field>{g}{perms}
    </record>''')


rule('legal_task_rule_lawyer', 'Matters: assigned (lawyer)', 'legal_task', ASSIGNED.format(p=''), 'group_legal_user')
rule('legal_task_rule_clerk', 'Matters: assigned (clerk)', 'legal_task', ASSIGNED.format(p=''), 'group_ldm_clerk')
rule('legal_task_rule_manager', 'Matters: all (manager)', 'legal_task', ALL, 'group_legal_manager')
rule('legal_task_rule_approver', 'Matters: in the approval flow (approver)', 'legal_task',
     "['|', ('approval_state', '!=', 'draft'), " + ASSIGNED.format(p='')[1:], 'group_ldm_approver')
NONCONF = "['|', ('confidential', '=', False), " + ASSIGNED.format(p='')[1:]
rule('legal_task_rule_see_all', 'Matters: every non-confidential matter (office-wide visibility)', 'legal_task', NONCONF, 'group_ldm_see_all')
rule('legal_task_rule_auditor', 'Matters: all (auditor, read)', 'legal_task', ALL, 'group_ldm_auditor', True, False, False, False)
rule('legal_task_rule_billing', 'Matters: non-confidential (billing, read)', 'legal_task', "[('confidential', '=', False)]", 'group_ldm_billing_user', True, False, False, False)

CLIENT = ("['|', '|', '|', ('lawyer_id', '=', user.id), ('lawyer_ids', 'in', [user.id]), "
          "('task_ids.lawyer_ids', 'in', [user.id]), ('task_ids.step_ids.user_id', '=', user.id)]")
rule('legal_company_rule_lawyer', 'Clients: assigned (lawyer)', 'legal_company', CLIENT, 'group_legal_user')
rule('legal_company_rule_clerk', 'Clients: assigned (clerk)', 'legal_company', CLIENT, 'group_ldm_clerk')
rule('legal_company_rule_manager', 'Clients: all (manager)', 'legal_company', ALL, 'group_legal_manager')
rule('legal_company_rule_see_all', 'Clients: all (office-wide visibility)', 'legal_company', ALL, 'group_ldm_see_all')
rule('legal_company_rule_auditor', 'Clients: all (auditor, read)', 'legal_company', ALL, 'group_ldm_auditor', True, False, False, False)
rule('legal_company_rule_billing', 'Clients: all (billing, read)', 'legal_company', ALL, 'group_ldm_billing_user', True, False, False, False)

CHILD = ASSIGNED.format(p='task_id.')
CHILDREN = (
    ('legal_task_step', 'Steps'), ('legal_task_document', 'Matter documents'), ('legal_hearing', 'Sessions'),
    ('legal_task_party', 'Parties'), ('legal_judgment', 'Judgments'), ('legal_task_expense', 'Expenses'),
    ('legal_time_entry', 'Time'), ('legal_court_stage', 'Court stages'),
)
for model, label in CHILDREN:
    rule(f'{model}_rule_assigned', f'{label}: of visible matters', model, CHILD, 'group_ldm_clerk')
    rule(f'{model}_rule_all', f'{label}: all', model, ALL, 'group_legal_manager')
    rule(f'{model}_rule_approver', f'{label}: of matters in the approval flow', model,
         "['|', ('task_id.approval_state', '!=', 'draft'), " + CHILD[1:], 'group_ldm_approver')
    rule(f'{model}_rule_see_all', f'{label}: of non-confidential matters (office-wide visibility)', model,
         "['|', ('task_id.confidential', '=', False), " + CHILD[1:], 'group_ldm_see_all')
    rule(f'{model}_rule_auditor', f'{label}: all (auditor, read)', model, ALL, 'group_ldm_auditor', True, False, False, False)
    rule(f'{model}_rule_billing', f'{label}: of non-confidential matters (billing)', model,
         "[('task_id.confidential', '=', False)]", 'group_ldm_billing_user')

DEADLINE = "['|', ('task_id', '=', False), " + CHILD[1:]
rule('legal_deadline_rule_assigned', 'Deadlines: of visible matters, and client deadlines', 'legal_deadline', DEADLINE, 'group_ldm_clerk')
rule('legal_deadline_rule_all', 'Deadlines: all', 'legal_deadline', ALL, 'group_legal_manager')
rule('legal_deadline_rule_see_all', 'Deadlines: of non-confidential matters (office-wide visibility)', 'legal_deadline',
     "['|', '|', ('task_id', '=', False), ('task_id.confidential', '=', False), " + CHILD[1:], 'group_ldm_see_all')
rule('legal_deadline_rule_auditor', 'Deadlines: all (auditor, read)', 'legal_deadline', ALL, 'group_ldm_auditor', True, False, False, False)
rule('legal_deadline_rule_billing', 'Deadlines: of non-confidential matters (billing, read)', 'legal_deadline',
     "['|', ('task_id', '=', False), ('task_id.confidential', '=', False)]", 'group_ldm_billing_user', True, False, False, False)

rule('legal_request_rule_own', 'Requests: own', 'legal_request', "[('requester_id', '=', user.id)]", 'group_ldm_requests')
rule('legal_request_rule_legal', 'Requests: all (legal team)', 'legal_request', ALL, 'group_ldm_clerk')
rule('legal_request_rule_auditor', 'Requests: all (auditor, read)', 'legal_request', ALL, 'group_ldm_auditor', True, False, False, False)

rule('legal_company_document_rule_team', 'Company documents: not confidential, or my client', 'legal_company_document',
     "['|', ('confidential', '=', False), ('legal_company_id.lawyer_id', '=', user.id)]", 'group_ldm_clerk')
rule('legal_company_document_rule_manager', 'Company documents: all (manager)', 'legal_company_document', ALL, 'group_legal_manager')
rule('legal_company_document_rule_auditor', 'Company documents: all (auditor, read)', 'legal_company_document', ALL, 'group_ldm_auditor', True, False, False, False)
rule('legal_company_document_rule_billing', 'Company documents: not confidential (billing)', 'legal_company_document',
     "[('confidential', '=', False)]", 'group_ldm_billing_user', True, False, False, False)

CORR = "['|', '|', ('task_id', '=', False), ('task_id.confidential', '=', False), " + CHILD[1:]
rule('legal_correspondence_rule_team', 'Correspondence: letters of visible matters, and general letters', 'legal_correspondence', CORR, 'group_ldm_clerk')
rule('legal_correspondence_rule_manager', 'Correspondence: all (manager)', 'legal_correspondence', ALL, 'group_legal_manager')
rule('legal_correspondence_rule_auditor', 'Correspondence: all (auditor, read)', 'legal_correspondence', ALL, 'group_ldm_auditor', True, False, False, False)
rule('legal_advance_rule_own', 'Advances: own', 'legal_advance', "[('user_id', '=', user.id)]", 'group_ldm_clerk')
rule('legal_advance_rule_all', 'Advances: all (manager)', 'legal_advance', ALL, 'group_legal_manager')
rule('legal_advance_rule_billing', 'Advances: all (billing)', 'legal_advance', ALL, 'group_ldm_billing_user')
rule('legal_advance_rule_auditor', 'Advances: all (auditor, read)', 'legal_advance', ALL, 'group_ldm_auditor', True, False, False, False)
FUNDS = "['|', ('task_id', '=', False), ('task_id.confidential', '=', False)]"
rule('legal_client_fund_line_rule_team', 'Client money: of non-confidential matters and general', 'legal_client_fund_line', FUNDS, 'group_ldm_clerk')
rule('legal_client_fund_line_rule_all', 'Client money: all (manager)', 'legal_client_fund_line', ALL, 'group_legal_manager')
rule('legal_client_fund_line_rule_billing', 'Client money: all (billing)', 'legal_client_fund_line', ALL, 'group_ldm_billing_user')
rule('legal_client_fund_line_rule_auditor', 'Client money: all (auditor, read)', 'legal_client_fund_line', ALL, 'group_ldm_auditor', True, False, False, False)
MULTI_COMPANY = (
    'legal_task', 'legal_company', 'legal_task_step', 'legal_task_document', 'legal_hearing', 'legal_task_party',
    'legal_judgment', 'legal_deadline', 'legal_task_expense', 'legal_time_entry', 'legal_engagement',
    'legal_engagement_line', 'legal_poa', 'legal_correspondence', 'legal_request', 'legal_company_document',
    'legal_obligation', 'legal_conflict_check', 'legal_task_template', 'legal_court_stage', 'legal_guarantee',
    'legal_client_fund_line', 'legal_advance',
)
for model in MULTI_COMPANY:
    rule(f'{model}_rule_company', f'{model.replace("_", ".")}: multi-company', model, COMPANY)
out.append('</odoo>')
with open('security/ldm_rules.xml', 'w', encoding='utf-8', newline='\n') as fh:
    fh.write('\n'.join(out) + '\n')
print(len(out) - 4, 'rules')
