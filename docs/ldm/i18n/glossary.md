# Arabic glossary for legal_department_management (ar_001)

Iraqi legal Arabic, not machine translation. The catalogue (`i18n/ar.po`) is
generated with `odoo-bin i18n export` and filled with these terms. Where a
column says "neutral", it is the word used in menus, actions and reports in
every mode; the mode-specific words appear only on the few labels the mode
relabels (SPEC §14.3).

## Core objects

| English source | Arabic | Notes |
|---|---|---|
| Matter / Matters | ملف / الملفات | neutral umbrella; the register title is «القضايا والمعاملات» |
| Matter type | نوع الملف | |
| New matter | ملف جديد | |
| Client / Clients (neutral) | الموكّل / الشركات والموكّلون | SAG's own label for the register |
| Client (department words) | الشركة | |
| Client (office words) | الموكّل | |
| Government transaction | معاملة حكومية | |
| Lawsuit | دعوى | |
| Execution | تنفيذ | execution file: إضبارة تنفيذية |
| Contract | عقد | |
| Legal opinion | رأي قانوني | opinion memo: مذكرة رأي قانوني |
| Company affairs | شؤون الشركات | |
| Investigation | تحقيق إداري | compensation ordered: التضمين |
| Body or court | الجهة أو المحكمة | |
| Bodies and courts | الجهات والمحاكم | |
| Ministry / authority | الوزارة / الهيئة | |
| Court session | جلسة | court sessions: الجلسات |
| Visit (to a counter) | مراجعة | "Log visit": سجّل المراجعة |
| Step | خطوة | |
| Documents to collect | المستمسكات المطلوبة | |
| Confirmed genuine (صحة صدور) | تأكيد صحة الصدور | state "Verified": مؤكد الصدور |
| Deadline | موعد نهائي / مهلة | statutory period: مدة قانونية |
| Act by | آخر موعد للإجراء | the safe date |
| Legal last day | آخر يوم قانونياً | after the holiday roll |
| Awaiting notification | بانتظار التبليغ | |
| Notified on | تاريخ التبليغ | |
| Judgment | حكم | final: اكتسب الدرجة القطعية |
| Appeal / Cassation / Objection | استئناف / تمييز / اعتراض على الحكم الغيابي | |
| Correction of a cassation decision | تصحيح القرار التمييزي | |
| Retrial | إعادة المحاكمة | |
| Grievance | تظلّم | |
| Left for review | تُركت للمراجعة | |
| Power of attorney | وكالة | authorisation: تخويل; revoke: عزل / إلغاء الوكالة |
| Substitution letter | كتاب إنابة | |
| Correspondence | الصادر والوارد | incoming: وارد; outgoing: صادر; register book: سجل الصادر والوارد |
| Letter template | قالب كتاب | |
| Request (to the legal team) | طلب خدمة قانونية | My requests: طلباتي |
| Letter of guarantee | خطاب ضمان | bid / performance / advance: دخول / حسن تنفيذ / سلفة |
| Fee agreement | عقد أتعاب | |
| Fees | الأتعاب | |
| Retainer | أتعاب المستشار القانوني الشهرية | |
| Instalment | قسط | |
| Client money | أمانات الموكلين | |
| Cash advance | سلفة | |
| Expense | مصروف | expenses: المصروفات |
| Receipt number | رقم الوصل | |
| Client statement | كشف حساب | |
| Conflict of interest check | فحص تعارض المصالح | |
| Hearing roll | رول الجلسات | |
| Follow-up sheet | استمارة متابعة | |
| Monthly status report | موقف الدعاوى والمعاملات | |
| My Day | مكتبي | |
| Agenda | الأجندة | |
| Registers | السجلات | |
| Approvals | الاعتمادات | Awaiting approval: بانتظار الاعتماد |
| Reporting | التقارير | |
| Configuration | الإعدادات | |

## Status words (plain nouns, no emoji)

| English | Arabic |
|---|---|
| New | جديد |
| In progress | قيد الإجراء |
| Waiting | بانتظار |
| Done | منجز |
| Cancelled | ملغى |
| Not requested | لم يُطلب |
| Awaiting approval | بانتظار الاعتماد |
| Approved | معتمد |
| Rejected | مرفوض |
| Planned / Held | مقررة / منعقدة |
| Open / Met / Missed | قائم / مُستوفى / فائت |

## Roles

| English | Arabic |
|---|---|
| Clerk / Runner | كاتب / معقّب |
| Lawyer | محامٍ |
| Approver | معتمِد |
| Legal Manager | المدير القانوني |
| Auditor / executive (read only) | مدقق / متابع (قراءة فقط) |
| Billing | المحاسبة القانونية |

## Style

- Month names follow Odoo's `ar_001` formatting in v1 (SPEC §13).
- Buttons are verbs in the imperative: «سجّل»، «اعتمد»، «ارفض»، «أغلق الملف».
- Empty states are two short lines: what is empty, what to do next.
- No Latin text on Arabic screens except identifiers (CASE/2026/…) and currency codes.
