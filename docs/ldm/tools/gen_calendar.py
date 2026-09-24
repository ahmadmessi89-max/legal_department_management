"""Generate data/ldm_calendar_data.xml: the Iraqi Sunday-Thursday calendar with the
public holidays of Law 12 of 2024 for 2026 and 2027. Hijri-dated holidays are
estimates (the endowment offices fix them each year) and say so in their names."""
import os
from datetime import date, datetime, time, timedelta

_here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
os.chdir(_here if os.path.exists(os.path.join(_here, "__manifest__.py"))
         else os.path.join(_here, "custom_addons", "legal_department_management"))
BAGHDAD = timedelta(hours=3)


def utc(d, end=False):
    local = datetime.combine(d, time(23, 59, 59) if end else time(0, 0, 0))
    return (local - BAGHDAD).strftime("%Y-%m-%d %H:%M:%S")


HOLIDAYS = {
    2026: [
        ("New Year's Day", date(2026, 1, 1), 1, False),
        ("Army Day", date(2026, 1, 6), 1, False),
        ("Memorial of the regime's crimes (Halabja)", date(2026, 3, 16), 1, False),
        ("Eid al-Fitr (estimated)", date(2026, 3, 20), 3, True),
        ("Nowruz", date(2026, 3, 21), 1, False),
        ("Labour Day", date(2026, 5, 1), 1, False),
        ("Eid al-Adha (estimated)", date(2026, 5, 27), 4, True),
        ("Eid al-Ghadir (estimated)", date(2026, 6, 4), 1, True),
        ("Islamic New Year (estimated)", date(2026, 6, 16), 1, True),
        ("Ashura (estimated)", date(2026, 6, 25), 1, True),
        ("Prophet's Birthday (estimated)", date(2026, 8, 25), 1, True),
    ],
    2027: [
        ("New Year's Day", date(2027, 1, 1), 1, False),
        ("Army Day", date(2027, 1, 6), 1, False),
        ("Eid al-Fitr (estimated)", date(2027, 3, 9), 3, True),
        ("Memorial of the regime's crimes (Halabja)", date(2027, 3, 16), 1, False),
        ("Nowruz", date(2027, 3, 21), 1, False),
        ("Labour Day", date(2027, 5, 1), 1, False),
        ("Eid al-Adha (estimated)", date(2027, 5, 16), 4, True),
        ("Eid al-Ghadir (estimated)", date(2027, 5, 24), 1, True),
        ("Islamic New Year (estimated)", date(2027, 6, 6), 1, True),
        ("Ashura (estimated)", date(2027, 6, 15), 1, True),
        ("Prophet's Birthday (estimated)", date(2027, 8, 14), 1, True),
    ],
}

lines = ['<?xml version="1.0" encoding="utf-8"?>', '<odoo noupdate="1">', '''    <!--
        The Iraqi working week (Law 12 of 2024: Friday and Saturday are the
        weekly holidays) and the general public holidays of the same law.
        Hijri holidays move every year and are fixed by the Shia and Sunni
        endowment offices, so their dates here are estimates marked as such.
        Review them every December; the legal manager gets a reminder.
    -->
    <record id="ldm_calendar_iraq" model="resource.calendar">
        <field name="name">Iraq — Sunday to Thursday (legal deadlines)</field>
        <field name="tz">Asia/Baghdad</field>
        <field name="company_id" eval="False"/>
        <field name="hours_per_day">6.5</field>
        <field name="attendance_ids" eval="[(5, 0, 0),''']
days = [("6", "Sunday"), ("0", "Monday"), ("1", "Tuesday"), ("2", "Wednesday"), ("3", "Thursday")]
att = []
for code, label in days:
    att.append(f"            (0, 0, {{'name': '{label}', 'dayofweek': '{code}', 'hour_from': 8.0, 'hour_to': 14.5, 'day_period': 'morning'}})")
lines.append(",\n".join(att) + "]\"/>")
lines.append("    </record>")
for year, items in HOLIDAYS.items():
    for index, (name, start, length, estimated) in enumerate(items, 1):
        end = start + timedelta(days=length - 1)
        lines.append(f'''    <record id="ldm_holiday_{year}_{index:02d}" model="resource.calendar.leaves">
        <field name="name">{name} {year}</field>
        <field name="calendar_id" ref="ldm_calendar_iraq"/>
        <field name="date_from">{utc(start)}</field>
        <field name="date_to">{utc(end, True)}</field>
        <field name="time_type">leave</field>
    </record>''')
lines.append("</odoo>")
with open("data/ldm_calendar_data.xml", "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines) + "\n")
print("calendar written")
