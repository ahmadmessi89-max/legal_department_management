import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { formatCurrency, getCurrency } from "@web/core/currency";

const { DateTime } = luxon;

/**
 * Formatting shared by every workspace component.
 *
 * Dates arrive from the server as ISO strings ("2026-09-24") and are shown
 * through luxon, which Odoo has already set to the reader's language and digit
 * system, so an OWL date reads exactly like a date in a native Odoo field.
 */

/** Whole dinars: nobody in Iraq writes fils, and "500,000.000" reads as a typo. */
export function formatAmount(amount, currencyId) {
    const currency = getCurrency(currencyId);
    const wholeUnits = !currency || currency.name === "IQD";
    return formatCurrency(amount || 0, currencyId, wholeUnits ? { digits: [69, 0] } : {});
}

/** The IQD formatter the brief asks for, by name. */
export function formatIQD(amount, currencyId) {
    return formatAmount(amount, currencyId);
}

export function parseDay(iso) {
    return iso ? DateTime.fromISO(iso) : null;
}

export function todayDay() {
    return DateTime.local().startOf("day");
}

/** Whole days from today to ``iso`` (negative in the past). */
export function daysFrom(iso, today = todayDay()) {
    const day = parseDay(iso);
    if (!day) {
        return null;
    }
    return Math.round(day.startOf("day").diff(today, "days").days);
}

/** "12 Oct", with the year only when it is not this year. */
export function shortDate(iso) {
    const day = parseDay(iso);
    if (!day) {
        return "";
    }
    return day.year === DateTime.local().year ? day.toFormat("d MMM") : day.toFormat("d MMM yyyy");
}

/** "Wednesday 24 September 2026" */
export function longDate(iso) {
    const day = parseDay(iso);
    return day ? day.toFormat("cccc d MMMM yyyy") : "";
}

/**
 * The date as a person says it, and the tone it earns: overdue is danger,
 * today and the next two days are warning, the rest is quiet.
 */
export function relativeDay(iso, today = todayDay()) {
    const days = daysFrom(iso, today);
    if (days === null) {
        return { label: _t("No date"), tone: "", days };
    }
    let label;
    if (days === 0) {
        label = _t("Today");
    } else if (days === 1) {
        label = _t("Tomorrow");
    } else if (days === -1) {
        label = _t("Yesterday");
    } else if (days < 0) {
        label = _t("%s days late", -days);
    } else if (days <= 6) {
        label = _t("In %s days", days);
    } else {
        label = shortDate(iso);
    }
    let tone = "";
    if (days < 0) {
        tone = "danger";
    } else if (days <= 2) {
        tone = "warning";
    }
    return { label, tone, days };
}

/** A day heading for agendas: "Today", "Tomorrow" or "Sunday 28 Sep". */
export function dayHeading(iso, today = todayDay()) {
    const days = daysFrom(iso, today);
    const day = parseDay(iso);
    const name = day ? day.toFormat("cccc d MMM") : "";
    if (days === 0) {
        return { title: _t("Today"), subtitle: name };
    }
    if (days === 1) {
        return { title: _t("Tomorrow"), subtitle: name };
    }
    return { title: name, subtitle: "" };
}

/** A float hour (13.5) as a clock time (13:30); empty when no time is set. */
export function formatHour(value) {
    if (!value) {
        return "";
    }
    const hours = Math.floor(value);
    const minutes = Math.round((value - hours) * 60);
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

/** The date in the Hijri (Umm al-Qura) calendar, in the reader's language. */
export function hijriDate(iso) {
    const day = parseDay(iso);
    if (!day) {
        return "";
    }
    const locale = (luxon.Settings.defaultLocale || "ar").split("-u-")[0];
    try {
        return new Intl.DateTimeFormat(`${locale}-u-ca-islamic-umalqura`, {
            day: "numeric",
            month: "long",
            year: "numeric",
            numberingSystem: luxon.Settings.defaultNumberingSystem || undefined,
        }).format(day.toJSDate());
    } catch {
        return "";
    }
}

/** The Lucide icon of each kind of row the workspace lists. */
export const ROW_ICONS = {
    step: "list-checks",
    visit: "building-2",
    hearing: "gavel",
    deadline: "hourglass",
    target: "flag",
    approval: "stamp",
    activity: "clock",
    notification: "mail",
    idle: "circle-dot",
    waiting: "hourglass",
    conflict: "shield-alert",
};

export const MATTER_KINDS = [
    "government", "litigation", "execution", "contract", "opinion", "corporate", "investigation", "other",
];

/** The class that tints a matter row's start-edge spine by its kind. */
export function kindClass(kind) {
    return `o_ldm_kind_${MATTER_KINDS.includes(kind) ? kind : "other"}`;
}

/** Remember that a stamp was just earned, so the page shows it landing once. */
export function markStampLanding(key) {
    try {
        browser.sessionStorage.setItem("ldm_stamp_land", String(key));
    } catch {
        // Only an animation is lost.
    }
}

/** True once for the stamp that was just earned. */
export function takeStampLanding(key) {
    try {
        if (browser.sessionStorage.getItem("ldm_stamp_land") === String(key)) {
            browser.sessionStorage.removeItem("ldm_stamp_land");
            return true;
        }
    } catch {
        // No storage: no animation.
    }
    return false;
}
