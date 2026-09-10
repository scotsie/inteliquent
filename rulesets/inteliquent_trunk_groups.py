#!/usr/bin/env python3
# Checkmk 2.3+ ruleset for Inteliquent trunk groups check parameters

from cmk.rulesets.v1 import Title, Help
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    Dictionary,
    DictElement,
    Integer,
    LevelDirection,
    SimpleLevels,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, Topic, HostAndItemCondition


def _form_inteliquent_trunks() -> Dictionary:
    return Dictionary(
        title=Title("Inteliquent Trunks"),
        help_text=Help(
            "Configure utilization thresholds and status mappings for Inteliquent trunks and groups. "
            "These settings apply to both individual trunk groups and logical trunk groups."
        ),
        elements={
            "utilization_levels": DictElement(
                parameter_form=SimpleLevels(
                    title=Title("Utilization levels"),
                    help_text=Help(
                        "Set warning and critical thresholds for trunk group utilization percentage. "
                        "Utilization is calculated as (inCalls + outCalls) / capacity * 100."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="%"),
                    prefill_fixed_levels=DefaultValue((80, 90)),
                ),
                required=True,
            ),
            "status_mapping": DictElement(
                parameter_form=Dictionary(
                    title=Title("Status mappings"),
                    help_text=Help(
                        "Configure how trunk group status values map to Checkmk monitoring states. "
                        "This allows you to customize the severity of different trunk states."
                    ),
                    elements={
                        "inservice": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("In Service status"),
                                help_text=Help("Monitoring state when trunk is 'In Service'"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warning", title=Title("WARNING")),
                                    SingleChoiceElement(name="critical", title=Title("CRITICAL")),
                                    SingleChoiceElement(name="unknown", title=Title("UNKNOWN")),
                                ],
                                prefill=DefaultValue("ok"),
                            ),
                            required=True,
                        ),
                        "pending": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("Pending status"),
                                help_text=Help("Monitoring state when trunk is 'Pending'"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warning", title=Title("WARNING")),
                                    SingleChoiceElement(name="critical", title=Title("CRITICAL")),
                                    SingleChoiceElement(name="unknown", title=Title("UNKNOWN")),
                                ],
                                prefill=DefaultValue("warning"),
                            ),
                            required=True,
                        ),
                        "pendingdisconnect": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("Pending Disconnect status"),
                                help_text=Help("Monitoring state when trunk is 'Pending Disconnect'"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warning", title=Title("WARNING")),
                                    SingleChoiceElement(name="critical", title=Title("CRITICAL")),
                                    SingleChoiceElement(name="unknown", title=Title("UNKNOWN")),
                                ],
                                prefill=DefaultValue("warning"),
                            ),
                            required=False,
                        ),
                        "other": DictElement(
                            parameter_form=SingleChoice(
                                title=Title("Other status"),
                                help_text=Help("Monitoring state for any other trunk status"),
                                elements=[
                                    SingleChoiceElement(name="ok", title=Title("OK")),
                                    SingleChoiceElement(name="warning", title=Title("WARNING")),
                                    SingleChoiceElement(name="critical", title=Title("CRITICAL")),
                                    SingleChoiceElement(name="unknown", title=Title("UNKNOWN")),
                                ],
                                prefill=DefaultValue("critical"),
                            ),
                            required=True,
                        ),
                    },
                ),
                required=True,
            ),
        },
    )


rule_spec_inteliquent_trunks = CheckParameters(
    name="inteliquent_trunks",
    title=Title("Inteliquent Trunks"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_inteliquent_trunks,
    condition=HostAndItemCondition(item_title=Title("Trunk Utilization")),
)