import { registry } from "@web/core/registry";
import { floatTimeField, FloatTimeField } from "@web/views/fields/float_time/float_time_field";
import { formatFloatTime } from "@web/views/fields/formatters";
import { parseFloatTime } from "@web/views/fields/parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";

/**
 * A clock time that may be unknown. A court session is often listed before
 * its hour is: the float is then 0, which Odoo's float_time shows as "00:00",
 * a time nobody sits at. This widget shows nothing (or the placeholder)
 * until an hour is entered, and an emptied input stores 0 again.
 */
export class LdmTimeField extends FloatTimeField {
    static template = "legal_department_management.LdmTimeField";
    static props = {
        ...FloatTimeField.props,
        placeholder: { type: String, optional: true },
    };

    setup() {
        this.inputFloatTimeRef = useInputField({
            getValue: () => this.formattedValue,
            refName: "numpadDecimal",
            parse: (value) => (value && value.trim() ? parseFloatTime(value) : 0),
        });
        useNumpadDecimal();
    }

    get formattedValue() {
        const value = this.props.record.data[this.props.name];
        return value ? formatFloatTime(value, { displaySeconds: this.props.displaySeconds }) : "";
    }
}

export const ldmTimeField = {
    ...floatTimeField,
    component: LdmTimeField,
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...floatTimeField.extractProps(fieldInfo, dynamicInfo),
        placeholder: fieldInfo.placeholder,
    }),
};

registry.category("fields").add("ldm_time", ldmTimeField);
