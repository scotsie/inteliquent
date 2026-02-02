#!/usr/bin/env python3
# Checkmk 2.3+/2.4+ ruleset for Inteliquent special agent (multi-account)

from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic, Title, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary, DictElement, List, String
)


def _form_special_agent_inteliquent_api() -> Dictionary:
    return Dictionary(
        title=Title("Inteliquent API (special agent)"),
        help_text=Help(
            "Configure one or more accounts. Each entry maps to a repeated command-line "
            "group:  --account COMPANY API_KEY API_SECRET"
        ),
        elements={
            "accounts": DictElement(
                parameter_form=List(
                    title=Title("Accounts"),
                    element_template=Dictionary(
                        title=Title("Account"),
                        elements={
                            "company": DictElement(
                                parameter_form=String(title=Title("Company")),
                                required=True,
                            ),
                            "api_key": DictElement(
                                parameter_form=String(title=Title("API key")),
                                required=True,
                            ),
                            "api_secret": DictElement(
                                parameter_form=String(title=Title("API secret")),
                                required=True,
                            ),
                        },
                    ),
                    editable_order=True,
                ),
                required=True,
            ),
            "logical_groups": DictElement(
                parameter_form=List(
                    title=Title("Logical Trunk Groups"),
                    help_text=Help(
                        "Define logical groupings of trunk groups. Metrics from member trunk groups "
                        "will be aggregated under a single service 'trunk group <group_name>'. "
                        "Trunk groups not assigned to a logical group will still be monitored individually. "
                        "Leave empty to monitor individual trunk groups only."
                    ),
                    element_template=Dictionary(
                        title=Title("Logical Group"),
                        elements={
                            "group_name": DictElement(
                                parameter_form=String(title=Title("Group Name")),
                                required=True,
                            ),
                            "trunk_group_members": DictElement(
                                parameter_form=List(
                                    title=Title("Member Trunk Groups"),
                                    element_template=String(
                                        title=Title("Trunk Group Name"),
                                        help_text=Help("Exact trunk group name from Inteliquent API")
                                    ),
                                ),
                                required=True,
                            ),
                        },
                    ),
                    editable_order=True,
                ),
                required=False,
            ),
        },
    )


rule_spec_inteliquent_api = SpecialAgent(
    name="inteliquent_api",
    title=Title("Inteliquent API"),
    topic=Topic.CLOUD,
    parameter_form=_form_special_agent_inteliquent_api,
)
