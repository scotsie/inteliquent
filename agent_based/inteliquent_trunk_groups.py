#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inteliquent trunk groups - agent-based check (Checkmk 2.3+ / API v2)

Section header expected from special agent:
    <<<inteliquent_trunk_groups:sep(0)>>>
    { ... JSON ... }

Discovery: one service per 'customerTrunkGroupName'
Check:
  - Status: OK if 'In Service' (case/space-insensitive), else CRIT, UNKNOWN if missing
  - Utilization: WARN >= 80%, CRIT >= 90%, UNKNOWN if missing
Metrics: inCalls, outCalls, capacity, utilization_pct (extra)
"""


import json
from typing import Any, Dict, Iterable, Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State
)

Section = Mapping[str, Dict[str, Any]]  # key: customerTrunkGroupName -> trunk dict


# --------------------------
# Parser
# --------------------------
def _extract_trunks(obj: Any, company: str = None) -> Iterable[Dict[str, Any]]:
    """Yield each trunk dict that contains 'customerTrunkGroupName', adding 'company' key."""
    if isinstance(obj, dict):
        # If this dict looks like a trunk, yields it
        if "customerTrunkGroupName" in obj:
            trunk = dict(obj)  # shallow copy
            if company:
                trunk["company"] = company
            yield trunk
        else:
            # Otherwise recurse into children, passing down the parent key as company
            for k, v in obj.items():
                yield from _extract_trunks(v, company=k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _extract_trunks(v, company=company)


def parse_inteliquent_trunk_groups(string_table: list[list[str]]) -> Section:
    """Parse trunk groups, explicitly mapping company names to each trunk group."""
    if not string_table:
        return {}

    try:
        raw = "".join(row[0] for row in string_table if row)
        payload = json.loads(raw)
    except Exception:
        return {}

    by_name: Dict[str, Dict[str, Any]] = {}
    # Explicitly iterate over companies and trunk groups
    for company, trunks in payload.items():
        if not isinstance(trunks, dict):
            continue
        for trunk_id, trunk_data in trunks.items():
            # Add company to trunk_data
            trunk = dict(trunk_data)
            trunk["company"] = company
            name = trunk.get("customerTrunkGroupName")
            if not isinstance(name, str) or not name.strip():
                continue
            by_name[name] = trunk
    return by_name


# --------------------------
# Discovery
# --------------------------
def discover_inteliquent_trunk_groups(section: Section) -> Iterable[Service]:
    for name in sorted(section.keys()):
        yield Service(item=name)


# --------------------------
# Check
# --------------------------
def _normalize_status(text: str) -> str:
    return "".join(text.lower().split())  # lower, remove spaces


def check_inteliquent_trunk_groups(item: str, section: Section) -> Iterable[Result | Metric]:
    data = section.get(item)
    if not data:
        yield Result(state=State.UNKNOWN, summary="No data for item")
        return
    else:
        yield Result(
            state=State.OK,
            summary=f"Type: {data.get('accessType', '?')}",
            details=(
                f"Sinch trunk {data.get('customerTrunkGroupName')} in company {data.get('company', 'MISSING')}\n"
                f"features:\ne911Enabled: {data.get('e911Enabled', '?')}\nType: {data.get('accessType', '?')}"
            )
        )

    # --- Status evaluation ---
    status = data.get("status")
    if isinstance(status, str):
        norm = _normalize_status(status)
        st = State.OK if norm == "inservice" else State.CRIT
        details = f"Status: {status}"

        yield Result(
            state=st,
            summary=f"Status: {status}",
            details=details
        )
    else:
        yield Result(
            state=State.UNKNOWN,
            summary="Status: missing",
        )

    # --- Utilization evaluation & metrics ---
    util = data.get("utilization") or {}
    in_calls = util.get("inCalls")
    out_calls = util.get("outCalls")
    capacity = util.get("capacity")
    active_sessions = util.get("active_sessions")

    # Always yield metrics if values are present
    if isinstance(in_calls, (int, float)):
        yield Metric("inCalls", float(in_calls))
    if isinstance(out_calls, (int, float)):
        yield Metric("outCalls", float(out_calls))
    if isinstance(capacity, (int, float)):
        yield Metric("capacity", float(capacity))
    if isinstance(active_sessions, (int, float)) and isinstance(capacity, (int, float)):
        if active_sessions != capacity:
            yield Result(
                state=State.WARN,
                notice=f"Active Sessions {active_sessions} does not match Capacity {capacity}."
            )

    if any(v is None for v in (in_calls, out_calls, capacity)) or not capacity:
        yield Result(state=State.UNKNOWN, summary="Utilization: missing")
        return

    try:
        used = float(in_calls) + float(out_calls)
        capf = float(capacity)
        pct = 100.0 * used / capf if capf else 0.0
        pcti = int(pct)
    except Exception:
        yield Result(state=State.UNKNOWN, summary="Utilization: invalid values")
        return

    if isinstance(pct, (int, float)):
        details = f"Utilization: {pct:.1f}% ({used:.0f}/{capf:.0f})\n"

        yield from check_levels(
            pcti,
            label="Utilization %",
            metric_name="utilization_pct",
            boundaries=(0, 100),
            render_func=lambda v: "%.1f%%" % v,
        )


# --------------------------
# Registration
# --------------------------
agent_section_inteliquent_api = AgentSection(
    name="inteliquent_trunk_groups",
    parse_function=parse_inteliquent_trunk_groups,
)

check_plugin_inteliquent_api = CheckPlugin(
    name="inteliquent_trunk_groups",
    service_name="trunk %s",
    discovery_function=discover_inteliquent_trunk_groups,
    check_function=check_inteliquent_trunk_groups,
)
