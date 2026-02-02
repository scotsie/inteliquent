#!/usr/bin/env python3
# Checkmk 2.3+/2.4+ server-side call for Inteliquent special agent (multi-account)

from cmk.server_side_calls.v1 import SpecialAgentConfig, SpecialAgentCommand, noop_parser


def _commands_from_params(params: dict, host_config):
    args = []

    # Global flag first (optional)
    if params.get("debug"):
        args.append("--debug")

    # Append one '--account COMPANY API_KEY API_SECRET' group for each entry
    for acct in params.get("accounts", []):
        company = acct.get("company")
        api_key = acct.get("api_key")
        api_secret = acct.get("api_secret")
        args += ["--account", company, api_key, api_secret]

    # Append logical groups configuration if defined
    logical_groups = params.get("logical_groups", [])
    if logical_groups:
        args.append("--logical-groups")
        # Pass groups as JSON for easier parsing on agent side
        import json
        groups_dict = {}
        for group in logical_groups:
            group_name = group.get("group_name")
            members = group.get("trunk_group_members", [])
            if group_name and members:
                groups_dict[group_name] = members
        if groups_dict:
            args.append(json.dumps(groups_dict))

    # Single command invocation with repeated '--account' segments
    yield SpecialAgentCommand(command_arguments=args)


special_agent_inteliquent_api = SpecialAgentConfig(
    name="inteliquent_api",
    parameter_parser=noop_parser,
    commands_function=_commands_from_params,
)
