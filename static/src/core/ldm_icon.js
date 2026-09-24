import { Component, xml } from "@odoo/owl";

/**
 * One icon language for the workspace: the Lucide subset vendored under
 * static/lib/lucide (ISC). Each icon is a CSS mask painted in currentColor
 * (static/src/scss/ldm_icons.scss), so it takes the colour and size of the
 * text around it. With a `title` the icon is announced; without one it is
 * decoration and hidden from screen readers.
 *
 *     <LdmIcon name="'gavel'"/>
 *     <LdmIcon name="'triangle-alert'" title="label.overdue" size="'lg'"/>
 */
export class LdmIcon extends Component {
    static template = xml`
        <span t-attf-class="o_ldm_icon o_ldm_icon_{{ props.name }} {{ props.size ? 'o_ldm_icon_' + props.size : '' }} {{ props.class || '' }}"
              t-att-role="props.title ? 'img' : undefined"
              t-att-aria-label="props.title ? '' + props.title : undefined"
              t-att-title="props.title ? '' + props.title : undefined"
              t-att-aria-hidden="props.title ? undefined : 'true'"/>`;
    static props = {
        name: String,
        // A translated label may arrive as a lazy translation object.
        title: { type: [String, Object], optional: true },
        size: { type: String, optional: true },
        class: { type: String, optional: true },
    };
}
