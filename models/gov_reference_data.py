# -*- coding: utf-8 -*-
"""The Iraqi reference library, as data (SPEC 9.2).

Loaded only when a manager presses "Load the Iraqi reference library" in
Settings; never shipped as module data, because SAG's unique-name constraints
would abort an upgrade on the first duplicate. The loader merges into existing
records by code, then by normalised Arabic name, and never duplicates.

Sources: research/02 section 5 (the ten bodies and 28 services of SAG's own
prototype), research/03 sections 6.1, 6.5 and 6.6 (courts, bodies, document
types). Body and court names are Arabic because that is how they are named in
Iraq; matter types, steps and document types carry English and Arabic.
Offsets are working days. "start" counts from the opening date, otherwise from
the previous step.
"""

# key, code, name, kind
MINISTRIES = [
    ("trade", "IQ-MOT", "وزارة التجارة", "ministry"),
    ("finance", "IQ-MOF", "وزارة المالية", "ministry"),
    ("labour", "IQ-MOLSA", "وزارة العمل والشؤون الاجتماعية", "ministry"),
    ("interior", "IQ-MOI", "وزارة الداخلية", "ministry"),
    ("justice", "IQ-MOJ", "وزارة العدل", "ministry"),
    ("foreign", "IQ-MOFA", "وزارة الخارجية", "ministry"),
    ("planning", "IQ-MOP", "وزارة التخطيط", "ministry"),
    ("communications", "IQ-MOC", "وزارة الاتصالات", "ministry"),
    ("electricity", "IQ-MOE", "وزارة الكهرباء", "ministry"),
    ("amanat", "IQ-AMB", "أمانة بغداد", "governorate"),
    ("cmc", "IQ-CMC", "هيئة الإعلام والاتصالات", "commission"),
    ("investment", "IQ-NIC", "الهيئة الوطنية للاستثمار", "commission"),
    ("chambers", "IQ-FICC", "اتحاد الغرف التجارية العراقية", "union"),
    ("transporters", "IQ-ITU", "اتحاد الناقلين", "union"),
    ("bar", "IQ-IBA", "نقابة المحامين العراقيين", "union"),
    ("sjc", "IQ-SJC", "مجلس القضاء الأعلى", "judicial"),
    ("state_council", "IQ-SC", "مجلس الدولة", "judicial"),
]

# Government bodies: key, ministry key, code, name, kind, extra values
BODIES = [
    ("registrar", "trade", "IQ-MOT-REG", "دائرة تسجيل الشركات", "registry",
     {"target_days": 10, "working_hours": "من 8:00 إلى 14:00", "addressee_title": "السيد مسجل الشركات المحترم"}),
    ("fairs", "trade", "IQ-MOT-FAIRS", "الشركة العامة للمعارض والخدمات التجارية", "government",
     {"target_days": 10, "working_hours": "من 8:00 إلى 14:00"}),
    ("tax", "finance", "IQ-MOF-GCT", "الهيئة العامة للضرائب", "government",
     {"target_days": 15, "working_hours": "من 8:00 إلى 14:00",
      "addressee_title": "السيد مدير عام الهيئة العامة للضرائب المحترم"}),
    ("customs", "finance", "IQ-MOF-GCC", "الهيئة العامة للكمارك", "government", {"target_days": 10}),
    ("social_security", "labour", "IQ-MOLSA-SS", "دائرة التقاعد والضمان الاجتماعي للعمال", "government",
     {"target_days": 10, "working_hours": "من 8:00 إلى 14:00"}),
    ("labour_office", "labour", "IQ-MOLSA-LAB", "دائرة العمل والتدريب المهني", "government", {"target_days": 15}),
    ("residency", "interior", "IQ-MOI-RES", "مديرية شؤون الإقامة", "government", {"target_days": 10}),
    ("traffic", "interior", "IQ-MOI-TRF", "المديرية العامة للمرور", "government",
     {"target_days": 5, "working_hours": "من 8:00 إلى 13:00"}),
    ("nationality", "interior", "IQ-MOI-NAT", "مديرية الجنسية والبطاقة الوطنية", "government", {"target_days": 10}),
    ("notary", "justice", "IQ-MOJ-NOT", "دائرة الكتاب العدول", "notary",
     {"target_days": 2, "working_hours": "من 8:00 إلى 14:00"}),
    ("real_estate", "justice", "IQ-MOJ-RE", "دائرة التسجيل العقاري", "registry", {"target_days": 20}),
    ("gazette", "justice", "IQ-MOJ-GAZ", "جريدة الوقائع العراقية", "government", {"target_days": 15}),
    ("authentication", "foreign", "IQ-MOFA-AUTH", "دائرة التصديقات", "government", {"target_days": 5}),
    ("contracts", "planning", "IQ-MOP-GC", "دائرة العقود الحكومية العامة", "government", {"target_days": 20}),
    ("post", "communications", "IQ-MOC-POST", "الشركة العامة للبريد والتوفير", "government", {"target_days": 5}),
    ("cmc_hq", "cmc", "IQ-CMC-HQ", "هيئة الإعلام والاتصالات – المقر العام", "government", {"target_days": 10}),
    ("electricity_dist", "electricity", "IQ-MOE-BGW", "مديرية توزيع كهرباء بغداد", "government", {"target_days": 10}),
    ("water", "amanat", "IQ-AMB-WTR", "دائرة ماء بغداد", "government", {"target_days": 10}),
    ("investment_hq", "investment", "IQ-NIC-HQ", "الهيئة الوطنية للاستثمار – المقر العام", "government",
     {"target_days": 15}),
    ("chamber_baghdad", "chambers", "IQ-FICC-BGW", "غرفة تجارة بغداد", "government",
     {"target_days": 5, "working_hours": "من 8:00 إلى 14:00"}),
    ("transporters_hq", "transporters", "IQ-ITU-HQ", "اتحاد الناقلين – المقر العام", "government", {"target_days": 5}),
    ("bar_hq", "bar", "IQ-IBA-HQ", "نقابة المحامين العراقيين – المقر العام", "government", {"target_days": 5}),
]

# Opening hours given to courts created by the library (written in words so the
# times read in the right order in a right-to-left line).
COURT_HOURS = "من 8:00 إلى 14:00"

# Courts of Baghdad: key, council key, code, name, kind, degree, higher court key.
# Listed so that every higher court comes before the courts below it.
COURTS = [
    ("cassation", "sjc", "IQ-SJC-CASS", "محكمة التمييز الاتحادية", "court", "cassation", None),
    ("appeal_karkh", "sjc", "IQ-SJC-APP-KRK", "محكمة استئناف بغداد/الكرخ الاتحادية", "court", "appeal", "cassation"),
    ("appeal_rusafa", "sjc", "IQ-SJC-APP-RSF", "محكمة استئناف بغداد/الرصافة الاتحادية", "court", "appeal", "cassation"),
    ("fi_karkh", "sjc", "IQ-SJC-FI-KRK", "محكمة بداءة الكرخ", "court", "first_instance", "appeal_karkh"),
    ("fi_mansour", "sjc", "IQ-SJC-FI-MNS", "محكمة بداءة المنصور", "court", "first_instance", "appeal_karkh"),
    ("fi_kadhimiya", "sjc", "IQ-SJC-FI-KDM", "محكمة بداءة الكاظمية", "court", "first_instance", "appeal_karkh"),
    ("fi_bayaa", "sjc", "IQ-SJC-FI-BYA", "محكمة بداءة البياع", "court", "first_instance", "appeal_karkh"),
    ("fi_commercial", "sjc", "IQ-SJC-FI-COM", "محكمة البداءة المتخصصة بالدعاوى التجارية", "court", "first_instance",
     "appeal_karkh"),
    ("fi_rusafa", "sjc", "IQ-SJC-FI-RSF", "محكمة بداءة الرصافة", "court", "first_instance", "appeal_rusafa"),
    ("fi_adhamiya", "sjc", "IQ-SJC-FI-ADH", "محكمة بداءة الأعظمية", "court", "first_instance", "appeal_rusafa"),
    ("fi_karrada", "sjc", "IQ-SJC-FI-KRD", "محكمة بداءة الكرادة", "court", "first_instance", "appeal_rusafa"),
    ("fi_new_baghdad", "sjc", "IQ-SJC-FI-NBG", "محكمة بداءة بغداد الجديدة", "court", "first_instance", "appeal_rusafa"),
    ("ps_karkh", "sjc", "IQ-SJC-PS-KRK", "محكمة الأحوال الشخصية في الكرخ", "court", "personal_status", "cassation"),
    ("ps_rusafa", "sjc", "IQ-SJC-PS-RSF", "محكمة الأحوال الشخصية في الرصافة", "court", "personal_status", "cassation"),
    ("labour_karkh", "sjc", "IQ-SJC-LAB-KRK", "محكمة العمل في الكرخ", "court", "labour", "appeal_karkh"),
    ("labour_rusafa", "sjc", "IQ-SJC-LAB-RSF", "محكمة العمل في الرصافة", "court", "labour", "appeal_rusafa"),
    ("felony_karkh", "sjc", "IQ-SJC-FEL-KRK", "محكمة جنايات الكرخ", "court", "felony", "cassation"),
    ("felony_rusafa", "sjc", "IQ-SJC-FEL-RSF", "محكمة جنايات الرصافة", "court", "felony", "cassation"),
    ("misd_karkh", "sjc", "IQ-SJC-MIS-KRK", "محكمة جنح الكرخ", "court", "misdemeanour", "felony_karkh"),
    ("misd_rusafa", "sjc", "IQ-SJC-MIS-RSF", "محكمة جنح الرصافة", "court", "misdemeanour", "felony_rusafa"),
    ("inv_karkh", "sjc", "IQ-SJC-INV-KRK", "محكمة تحقيق الكرخ", "court", "investigation", "felony_karkh"),
    ("inv_rusafa", "sjc", "IQ-SJC-INV-RSF", "محكمة تحقيق الرصافة", "court", "investigation", "felony_rusafa"),
    ("admin_high", "state_council", "IQ-SC-HAC", "المحكمة الإدارية العليا", "court", "administrative", None),
    ("admin", "state_council", "IQ-SC-ADM", "محكمة القضاء الإداري", "court", "administrative", "admin_high"),
    ("employees", "state_council", "IQ-SC-EMP", "محكمة قضاء الموظفين", "court", "employee", "admin_high"),
    ("exe_karkh", "justice", "IQ-MOJ-EXE-KRK", "مديرية تنفيذ الكرخ", "execution", "execution", "appeal_karkh"),
    ("exe_rusafa", "justice", "IQ-MOJ-EXE-RSF", "مديرية تنفيذ الرصافة", "execution", "execution", "appeal_rusafa"),
]

# Document types: code, English, Arabic, category, validity, days
DOCUMENT_TYPES = [
    ("national_id", "Unified national ID card", "البطاقة الوطنية الموحدة", "identity", "expiry_date", 0),
    ("passport", "Passport", "جواز السفر", "identity", "expiry_date", 0),
    ("residence_card", "Residence card", "بطاقة السكن", "identity", "none", 0),
    ("photos", "Personal photographs", "صور شخصية", "identity", "freshness_days", 180),
    ("residency_permit", "Residency permit", "الإقامة", "identity", "expiry_date", 0),
    ("work_permit", "Work permit", "إجازة العمل", "identity", "expiry_date", 0),
    ("incorporation_certificate", "Certificate of incorporation", "شهادة تأسيس الشركة", "registry", "none", 0),
    ("articles", "Articles of association", "عقد التأسيس", "registry", "none", 0),
    ("md_appointment", "Minutes appointing the managing director", "محضر تعيين المدير المفوض", "registry", "none", 0),
    ("ga_minutes", "General assembly minutes", "محضر اجتماع الهيئة العامة", "registry", "none", 0),
    ("final_accounts", "Audited final accounts", "الحسابات الختامية المدققة", "registry", "fixed_days", 365),
    ("capital_deposit", "Bank confirmation of the capital deposit", "تأييد مصرفي بإيداع رأس المال", "registry",
     "freshness_days", 90),
    ("registrar_confirmation", "Registrar's confirmation letter", "تأييد صادر من مسجل الشركات", "registry",
     "freshness_days", 90),
    ("lease", "Certified lease contract", "عقد إيجار مصدق", "contract", "expiry_date", 0),
    ("electricity_bill", "Paid electricity bill", "قائمة كهرباء مسددة", "receipt", "freshness_days", 90),
    ("tax_card", "Tax card", "البطاقة الضريبية", "tax", "expiry_date", 0),
    ("tax_clearance", "Tax clearance", "براءة الذمة الضريبية", "tax", "expiry_date", 0),
    ("tax_return", "Annual tax return", "الإقرار الضريبي السنوي", "tax", "none", 0),
    ("ss_registration", "Social security registration certificate", "شهادة تسجيل المشروع في الضمان الاجتماعي",
     "social_security", "none", 0),
    ("ss_clearance", "Social security clearance", "براءة ذمة الضمان الاجتماعي", "social_security", "expiry_date", 0),
    ("chamber_id", "Chamber of commerce ID", "هوية غرفة التجارة", "chamber", "expiry_date", 0),
    ("trade_name", "Trade name reservation", "موافقة حجز الاسم التجاري", "chamber", "fixed_days", 90),
    ("import_licence", "Import licence", "إجازة الاستيراد", "registry", "expiry_date", 0),
    ("vehicle_registration", "Vehicle registration (annual)", "سنوية المركبة", "other", "expiry_date", 0),
    ("poa_general", "General power of attorney", "وكالة عامة", "poa", "expiry_date", 0),
    ("poa_special", "Special power of attorney", "وكالة خاصة", "poa", "expiry_date", 0),
    ("runner_authorisation", "Runner's authorisation letter", "وثيقة تخويل المراجع", "poa", "expiry_date", 0),
    ("payment_receipt", "Payment receipt", "وصل تسديد", "receipt", "none", 0),
    ("official_letter", "Official letter", "كتاب رسمي", "letter", "none", 0),
    ("judgment", "Court judgment", "قرار / حكم", "court", "none", 0),
]


def _s(en, ar, offset, visit=False, start=False):
    return {"en": en, "ar": ar, "offset": offset, "visit": visit, "start": start}


# Services: code, body key, English, Arabic, duration, coverage, steps, documents (code, mandatory)
SERVICES = [
    ("SVC-CMC-A", "cmc_hq", "Reserve or renew an .iq domain", "حجز نطاق أو تجديده", 10, True, [
        _s("Prepare the request and the documents", "تهيئة الطلب والمستمسكات", 2, start=True),
        _s("Submit the request at the commission", "تقديم الطلب إلى الهيئة", 1, visit=True),
        _s("Pay the fee and collect the registration", "دفع الرسم واستلام التسجيل", 5, visit=True),
    ], [("incorporation_certificate", True), ("runner_authorisation", True)]),
    ("SVC-CMC-B", "post", "Rent or renew a P.O. box", "صندوق البريد أو تجديده", 5, True, [
        _s("Submit the application at the post office", "تقديم الطلب إلى دائرة البريد", 2, visit=True, start=True),
        _s("Pay and collect the contract", "التسديد واستلام العقد", 3, visit=True),
    ], [("incorporation_certificate", True), ("runner_authorisation", True)]),
    ("SVC-UTIL-A", "electricity_dist", "Settle meters, subscriptions and utility clearance",
     "تسوية العدادات والاشتراكات وبراءة الذمة للماء والكهرباء", 12, False, [
        _s("Ask for the meter reading and the statement", "طلب قراءة العداد وكشف الحساب", 2, visit=True, start=True),
        _s("Pay the outstanding bills", "تسديد القوائم المترتبة", 2, visit=True),
        _s("Collect the clearance letter", "استلام كتاب براءة الذمة", 5, visit=True),
    ], [("lease", True), ("electricity_bill", True), ("runner_authorisation", True)]),
    ("SVC-REG-A", "registrar", "Certify company records at the Companies Registrar",
     "تصديق أوليات الشركات من دائرة مسجل الشركات", 8, False, [
        _s("Prepare the records to certify", "تهيئة الأوليات المطلوب تصديقها", 2, start=True),
        _s("Submit them at the registrar", "تقديمها إلى دائرة المسجل", 1, visit=True),
        _s("Collect the certified copies", "استلام النسخ المصدقة", 5, visit=True),
    ], [("articles", True), ("incorporation_certificate", True), ("runner_authorisation", True)]),
    ("SVC-REG-B", "registrar", "File the final accounts with the Companies Registrar",
     "تقديم الحسابات الختامية إلى دائرة مسجل الشركات", 25, True, [
        _s("Obtain the audited final accounts", "استحصال الحسابات الختامية المدققة", 10, start=True),
        _s("Hold the general assembly and sign the minutes", "عقد الهيئة العامة وتوقيع المحضر", 5),
        _s("File the accounts at the registrar", "تقديم الحسابات إلى دائرة المسجل", 2, visit=True),
        _s("Collect the filing receipt", "استلام وصل الإيداع", 5, visit=True),
    ], [("final_accounts", True), ("ga_minutes", True), ("incorporation_certificate", True)]),
    ("SVC-REG-C", "registrar", "Pay the registrar's fees and submit applications", "دفع الرسوم وتقديم الطلبات", 3, False, [
        _s("Prepare the application", "تهيئة الطلب", 1, start=True),
        _s("Pay the fees at the registrar's cashier", "دفع الرسوم في صندوق الدائرة", 1, visit=True),
        _s("Submit the application and keep the receipt", "تقديم الطلب والاحتفاظ بالوصل", 0, visit=True),
    ], [("runner_authorisation", True)]),
    ("SVC-REG-D", "registrar", "Confirmation of issuance of company records", "صحة صدور الأوليات", 8, False, [
        _s("Submit the confirmation request", "تقديم طلب صحة الصدور", 1, visit=True, start=True),
        _s("Collect the confirmation letter", "استلام كتاب صحة الصدور", 7, visit=True),
    ], [("articles", True), ("runner_authorisation", True)]),
    ("SVC-TAX-A", "tax", "Company tax assessment", "التحاسب الضريبي للشركات", 30, True, [
        _s("Prepare the financial statements for tax", "إعداد البيانات المالية لأغراض الضريبة", 10, start=True),
        _s("Submit the tax file", "تقديم الملف الضريبي", 2, visit=True),
        _s("Attend the assessment", "حضور التقدير", 10, visit=True),
        _s("Pay the tax and collect the receipt", "تسديد الضريبة واستلام الوصل", 3, visit=True),
    ], [("final_accounts", True), ("tax_card", True), ("tax_return", True), ("runner_authorisation", True)]),
    ("SVC-TAX-B", "tax", "Submit the tax accounts", "تقديم الحسابات الضريبية", 10, True, [
        _s("Prepare the return and the statements", "إعداد الإقرار والبيانات", 5, start=True),
        _s("Submit them at the companies section", "تقديمها إلى قسم الشركات", 1, visit=True),
        _s("Collect the submission receipt", "استلام وصل التقديم", 3, visit=True),
    ], [("tax_return", True), ("final_accounts", True), ("tax_card", True)]),
    ("SVC-TAX-C", "tax", "Tax clearance for companies", "براءة ذمة للشركات", 12, True, [
        _s("Collect the documents", "جمع المستمسكات", 2, start=True),
        _s("Submit the clearance request", "تقديم طلب براءة الذمة", 1, visit=True),
        _s("Follow up with the assessment section", "المتابعة مع قسم التقدير", 5, visit=True),
        _s("Collect the clearance letter", "استلام كتاب براءة الذمة", 3, visit=True),
    ], [("tax_card", True), ("final_accounts", True), ("incorporation_certificate", True),
        ("runner_authorisation", True)]),
    ("SVC-TAX-D", "tax", "Confirmation of issuance of clearance letters", "صحة صدور كتب براءة الذمة", 8, False, [
        _s("Submit the confirmation request", "تقديم طلب صحة الصدور", 1, visit=True, start=True),
        _s("Collect the confirmation", "استلام تأييد صحة الصدور", 7, visit=True),
    ], [("tax_clearance", True)]),
    ("SVC-TAX-E", "tax", "Tax on the salary of a foreign branch manager",
     "التحاسب على رواتب مدير الفرع للشركات الأجنبية", 10, True, [
        _s("Prepare the salary statement", "إعداد كشف الرواتب", 3, start=True),
        _s("Submit it at the withholding section", "تقديمه إلى قسم الاستقطاع المباشر", 1, visit=True),
        _s("Pay and collect the receipt", "التسديد واستلام الوصل", 5, visit=True),
    ], [("passport", True), ("residency_permit", True), ("work_permit", False)]),
    ("SVC-TAX-F", "tax", "Renew the company tax card", "تجديد هويات الشركات", 6, True, [
        _s("Submit the renewal request", "تقديم طلب التجديد", 1, visit=True, start=True),
        _s("Collect the renewed card", "استلام الهوية المجددة", 5, visit=True),
    ], [("tax_card", True), ("tax_clearance", True)]),
    ("SVC-TRF-A", "traffic", "Annual vehicle registration in the managing director's name",
     "تجديد السنويات للشركات (باسم المدير المفوض)", 4, True, [
        _s("Take the vehicle to the inspection", "فحص المركبة", 1, visit=True, start=True),
        _s("Pay the fees", "دفع الرسوم", 0, visit=True),
        _s("Collect the registration", "استلام السنوية", 2, visit=True),
    ], [("vehicle_registration", True), ("national_id", True), ("runner_authorisation", True)]),
    ("SVC-TRF-B", "traffic", "Issue new company badges in the managing director's name",
     "إصدار باجات جديدة للشركات (باسم المدير المفوض)", 10, False, [
        _s("Submit the badge application", "تقديم طلب الباج", 1, visit=True, start=True),
        _s("Wait for the security check and approval", "انتظار التدقيق الأمني والموافقة", 5),
        _s("Collect the badges", "استلام الباجات", 2, visit=True),
    ], [("national_id", True), ("photos", True), ("official_letter", True)]),
    ("SVC-TRF-C", "traffic", "Confirmation of issuance of powers of attorney and company papers",
     "صحة صدور وكالات وأوراق الشركة", 6, False, [
        _s("Submit the confirmation request", "تقديم طلب صحة الصدور", 1, visit=True, start=True),
        _s("Collect the confirmation", "استلام تأييد صحة الصدور", 5, visit=True),
    ], [("poa_special", True)]),
    ("SVC-SS-A", "social_security", "Pay social security contributions", "تسديد اشتراكات الضمان للشركات المشمولة", 3, False, [
        _s("Prepare the monthly statement of workers", "إعداد الكشف الشهري بأسماء العمال", 2, start=True),
        _s("Pay at the contributions section and collect the receipt", "التسديد في قسم الاشتراكات واستلام الوصل", 1,
           visit=True),
    ], [("ss_registration", True)]),
    ("SVC-SS-B", "social_security", "Answer a social security inspection report", "التقارير التفتيشية للشركات", 8, True, [
        _s("Receive the inspectors and note their findings", "استقبال المفتشين وتدوين الملاحظات", 0, start=True),
        _s("Prepare the answer to the report", "إعداد الإجابة على التقرير", 5),
        _s("Submit the answer", "تقديم الإجابة", 1, visit=True),
    ], [("ss_registration", True)]),
    ("SVC-SS-C", "social_security", "Social security clearance for companies", "براءة ذمة الشركات", 10, True, [
        _s("Submit the clearance request", "تقديم طلب براءة الذمة", 1, visit=True, start=True),
        _s("Follow up the request", "متابعة الطلب", 5, visit=True),
        _s("Collect the clearance", "استلام براءة الذمة", 3, visit=True),
    ], [("ss_registration", True), ("payment_receipt", True)]),
    ("SVC-SS-D", "social_security", "Register the hiring or resignation of employees", "استقالة وتعيين الموظفين", 5, False, [
        _s("Prepare the forms", "تهيئة الاستمارات", 1, start=True),
        _s("Submit them at the registration section", "تقديمها إلى قسم التسجيل", 1, visit=True),
        _s("Collect the approval", "استلام الموافقة", 3, visit=True),
    ], [("national_id", True), ("photos", False)]),
    ("SVC-CHM-A", "chamber_baghdad", "Renew the company ID at the Chamber of Commerce",
     "تجديد هويات الشركات من غرفة التجارة", 6, True, [
        _s("Collect the documents", "جمع المستمسكات", 2, start=True),
        _s("Submit the renewal", "تقديم طلب التجديد", 1, visit=True),
        _s("Pay the fee and collect the ID", "دفع الرسم واستلام الهوية", 3, visit=True),
    ], [("chamber_id", True), ("incorporation_certificate", True), ("tax_clearance", False),
        ("runner_authorisation", True)]),
    ("SVC-CHM-B", "fairs", "Import licence for companies", "إجازات الاستيراد للشركات من مسجل الشركات", 12, True, [
        _s("Submit the licence application", "تقديم طلب الإجازة", 2, visit=True, start=True),
        _s("Follow up the approval", "متابعة الموافقة", 5, visit=True),
        _s("Collect the licence", "استلام الإجازة", 3, visit=True),
    ], [("chamber_id", True), ("tax_clearance", True), ("incorporation_certificate", True)]),
    ("SVC-TRN-A", "transporters_hq", "Renew a transport company's ID", "تجديد هويات شركات النقل", 4, True, [
        _s("Submit the renewal", "تقديم طلب التجديد", 1, visit=True, start=True),
        _s("Collect the renewed ID", "استلام الهوية المجددة", 3, visit=True),
    ], [("incorporation_certificate", True), ("chamber_id", True)]),
    ("SVC-NOT-A", "notary", "Power of attorney for drivers, lawyers and staff", "وكالات للسواق والمحامين والموظفين", 3, False, [
        _s("Draft the power of attorney", "صياغة الوكالة", 1, start=True),
        _s("Sign it before the notary", "التوقيع أمام الكاتب العدل", 1, visit=True),
        _s("Collect the registered copy", "استلام النسخة المسجلة", 1, visit=True),
    ], [("national_id", True), ("md_appointment", True)]),
    ("SVC-NOT-B", "notary", "Certify a power of attorney", "تصديق الوكالات", 3, False, [
        _s("Submit it for certification", "تقديمها للتصديق", 1, visit=True, start=True),
        _s("Collect the certified copy", "استلام النسخة المصدقة", 2, visit=True),
    ], [("poa_special", True)]),
    ("SVC-NOT-C", "notary", "Confirmation of issuance of a power of attorney", "صحة صدور الوكالات", 3, False, [
        _s("Check the QR reference or ask for confirmation", "التحقق من رمز الاستجابة أو طلب صحة الصدور", 1,
           visit=True, start=True),
        _s("Record the confirmation", "تسجيل نتيجة صحة الصدور", 2),
    ], [("poa_special", True)]),
    ("SVC-NOT-D", "notary", "Notarial notice and revocation of a power of attorney", "إنذار وعزل الوكالات", 8, False, [
        _s("Draft the notice or the revocation", "صياغة الإنذار أو العزل", 1, start=True),
        _s("Register it at the notary", "تسجيله لدى الكاتب العدل", 1, visit=True),
        _s("Serve it on the agent", "تبليغ الوكيل", 5),
    ], [("poa_special", True), ("national_id", True)]),
    ("SVC-TAX-G", "tax", "Personal tax assessment and clearance of the managing director",
     "التحاسب الضريبي الشخصي وبراءة الذمة للمدير المفوض", 12, True, [
        _s("Collect the documents", "جمع المستمسكات", 2, start=True),
        _s("Submit the personal return", "تقديم الإقرار الشخصي", 1, visit=True),
        _s("Attend the assessment", "حضور التقدير", 5, visit=True),
        _s("Pay and collect the clearance", "التسديد واستلام براءة الذمة", 3, visit=True),
    ], [("national_id", True), ("residence_card", True)]),
]
