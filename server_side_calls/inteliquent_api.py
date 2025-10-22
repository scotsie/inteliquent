#!/usr/bin/env python3
# Checkmk 2.3+/2.4+ server-side call for Inteliquent special agent (multi-account)

from cmk.server_side_calls.v1 import SpecialAgentConfig, SpecialAgentCommand, noop_parser


def _commands_from_params(params: dict, host_config):
    args = []

    # Global flag first (optional)
    if params.get("debug"):
        args.append("--debug")

    # Append one '--account API_KEY API_SECRET LABEL' group for each entry
    for acct in params.get("accounts", []):
        company = acct.get("company")
        api_key = acct.get("api_key")
        api_secret = acct.get("api_secret")
        args += ["--account", company, api_key, api_secret]

    # Single command invocation with repeated '--account' segments
    yield SpecialAgentCommand(command_arguments=args)


special_agent_inteliquent_api = SpecialAgentConfig(
    name="inteliquent_api",
    parameter_parser=noop_parser,
    commands_function=_commands_from_params,
)
