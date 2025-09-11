#!/usr/bin/env python3
# Checkmk 2.3+/2.4+ ruleset for Inteliquent special agent (multi-account)

from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic, Title, Help
from cmk.rulesets.v1.form_specs import (
    Dictionary, DictElement, List, String, BooleanChoice, DefaultValue,
    # If you want password store fields, uncomment:
    # Password,
)


def _migrate_single_to_list(params: dict) -> dict:
    """Backward-compat: if the old single-account keys exist, convert to 'accounts' list.

    Old keys (example): api_key, api_secret, label, debug
    New shape: {'accounts': [{'api_key': ..., 'api_secret': ..., 'label': ...}], 'debug': ...}
    """
    if "accounts" in params:
        return params

    # Detect old single-account config
    if all(k in params for k in ("api_key", "api_secret", "label")):
        params = dict(params)  # shallow copy
        single = {
            "api_key": params.pop("api_key"),
            "api_secret": params.pop("api_secret"),
            "label": params.pop("label"),
        }
        params["accounts"] = [single]
    return params


def _form_special_agent_inteliquent_api() -> Dictionary:
    return Dictionary(
        title=Title("Inteliquent API (special agent)"),
        help_text=Help(
            "Configure one or more accounts. Each entry maps to a repeated command-line "
            "group:  --account API_KEY API_SECRET LABEL"
        ),
        migrate=_migrate_single_to_list,
        elements={
            "accounts": DictElement(
                parameter_form=List(
                    title=Title("Accounts"),
                    element_template=Dictionary(
                        title=Title("Account"),
                        elements={
                            "api_key": DictElement(
                                parameter_form=String(title=Title("API key")),
                                required=True,
                            ),
                            "api_secret": DictElement(
                                parameter_form=String(title=Title("API secret")),
                                required=True,
                            ),
                            "label": DictElement(
                                parameter_form=String(title=Title("Label")),
                                required=True,
                            ),
                        },
                    ),
                    editable_order=True,
                ),
                required=True,
            ),
            "debug": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Enable --debug"),
                    prefill=DefaultValue(False),
                ),
                required=False,
            ),
        },
    )


rule_spec_inteliquent_api = SpecialAgent(
    name="inteliquent_api",                # refers to executable 'agent_inteliquent_api'
    title=Title("Inteliquent API"),
    topic=Topic.CLOUD,
    parameter_form=_form_special_agent_inteliquent_api,
)
