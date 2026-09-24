import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";

/**
 * While the user is inside the Legal app (or the requesters' app), the body
 * carries `o_ldm_app`, so the top bar takes the ink of the title bands
 * instead of Odoo's own colour. Every other app keeps Odoo's look.
 */
const LEGAL_APPS = new Set([
    "legal_department_management.menu_legal_root",
    "legal_department_management.menu_ldm_requests_root",
]);

export const ldmAppThemeService = {
    dependencies: ["menu"],
    start(env, { menu }) {
        const update = () => {
            const app = menu.getCurrentApp();
            document.body.classList.toggle("o_ldm_app", Boolean(app && LEGAL_APPS.has(app.xmlid)));
        };
        env.bus.addEventListener("MENUS:APP-CHANGED", update);
        update();
    },
};

registry.category("services").add("ldm_app_theme", ldmAppThemeService);

// A calendar arch cannot carry a class, so the module's calendars name this
// js_class instead: the view root then carries `o_ldm_calendar_view`, which
// publishes the design tokens (ldm_tokens.scss).
registry.category("views").add("ldm_calendar", calendarView);
