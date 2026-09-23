# -*- coding: utf-8 -*-
{
    'name': 'قسم الشؤون القانونية والمحاماة المتطور',
    'version': '19.0.6.3.0',
    'category': 'Legal',
    'summary': 'نظام متكامل وتفاعلي لإدارة الشركات الموكلة، القضايا، المعاملات، والمستندات القانونية',
    'description': """
نظام الشؤون القانونية والمحاماة التفاعلي:
- لوحة تحكم ومتابعة ذكية متطورة (Interactive Legal Dashboard).
- إدارة متكاملة للشركات والموكلين وتفاصيل تسجيلهم.
- نافذة مخصصة لبدء القضايا والمعاملات.
- إدارة ديناميكية للدوائر والجهات الرسمية الحكومية.
- تعدد المحامين على مستوى الشركات والقضايا.
- تقارير PDF احترافية لملف كل شركة أو تقرير الرقابة الشامل لكافة القضايا والشركات واستمارة القضية.
- مهام مجدولة وتنبيهات ذكية لمواعيد الجلسات والاستحقاقات (Smart Session Cron & Activities).
- صلاحيات أمان مشددة وحظر حذف المعاملات لغير المدراء.
- الرقابة العامة والصلاحيات والموافقات للمدير القانوني ومدير النظام.
    """,
    'author': 'SAG Group',
    'depends': ['base', 'mail', 'hr', 'account'],
    'data': [
        'security/legal_security.xml',
        'security/ir.model.access.csv',
        'data/legal_department_data.xml',
        'data/legal_cron.xml',
        'report/legal_company_report_templates.xml',
        'report/legal_task_report_templates.xml',
        'report/legal_general_report_templates.xml',
        'views/legal_department_views.xml',
        'views/legal_task_wizard_views.xml',
        'views/legal_company_report_wizard_views.xml',
        'views/legal_general_report_wizard_views.xml',
        'views/legal_task_views.xml',
        'views/legal_company_views.xml',
        'views/legal_dashboard_views.xml',
        'views/legal_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'legal_department_management/static/src/dashboard/legal_dashboard.scss',
            'legal_department_management/static/src/dashboard/legal_dashboard.js',
            'legal_department_management/static/src/dashboard/legal_dashboard.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
