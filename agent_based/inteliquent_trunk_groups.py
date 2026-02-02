#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inteliquent trunk groups - agent-based check (Checkmk 2.3+ / API v2)

Section header expected from special agent:
    <<<inteliquent_trunks:sep(0)>>>
    { ... JSON ... }

Discovery:
  - One service per individual 'customerTrunkGroupName' (if not in a logical group)
  - One service per logical group ('trunk group <group_name>')

Check (Individual Trunks):
  - Status: OK if 'In Service', WARN if 'Pending', CRIT if other, UNKNOWN if missing
  - Utilization: WARN >= 80%, CRIT >= 90%, UNKNOWN if missing

Check (Logical Groups):
  - Status: OK if all members In Service
  - Status: WARN if 1+ members Pending or not In Service (with indicator of problematic member)
  - Status: CRIT if ALL members Pending or not In Service
  - Utilization: Aggregated from all member trunks

Metrics: inCalls, outCalls, capacity, utilization_pct
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
    State,
)

Section = Mapping[str, Any]  # Contains individual trunks, grouped trunks, and metadata

# Default check parameters
DEFAULT_PARAMS = {
    "utilization_levels": ("fixed", (80, 90)),  # SimpleLevels format: (type, (warn, crit))
    "status_mapping": {
        "inservice": 0,  # OK
        "pending": 1,    # WARN
        "other": 2,      # CRIT
    }
}


# --------------------------
# Parser
# --------------------------
def parse_inteliquent_trunk_groups(string_table: list[list[str]]) -> Section:
    """
    Parse trunk groups and logical group definitions.
    Returns dict with:
      - '__logical_groups__': dict of logical group definitions (group_name -> [members])
      - '__trunks__': dict of all individual trunks (customerTrunkGroupName -> trunk_data)
      - '__grouped_trunks__': set of trunk names that belong to logical groups
    """
    if not string_table:
        return {
            "__logical_groups__": {},
            "__trunks__": {},
            "__grouped_trunks__": set(),
        }

    try:
        raw = "".join(row[0] for row in string_table if row)
        payload = json.loads(raw)
    except Exception:
        return {
            "__logical_groups__": {},
            "__trunks__": {},
            "__grouped_trunks__": set(),
        }

    logical_groups = payload.get("__logical_groups__", {})
    
    # Build mapping of which trunk names belong to logical groups
    grouped_trunks = set()
    for group_name, members in logical_groups.items():
        grouped_trunks.update(members)

    trunks: Dict[str, Dict[str, Any]] = {}
    
    # Iterate over companies and extract all individual trunks
    for key, value in payload.items():
        if key.startswith("__"):
            # Skip metadata keys
            continue
        if not isinstance(value, dict):
            continue
        
        # key is company name, value is dict of trunks
        for trunk_id, trunk_data in value.items():
            trunk = dict(trunk_data)
            trunk["company"] = key
            name = trunk.get("customerTrunkGroupName")
            if not isinstance(name, str) or not name.strip():
                continue
            trunks[name] = trunk

    return {
        "__logical_groups__": logical_groups,
        "__trunks__": trunks,
        "__grouped_trunks__": grouped_trunks,
    }


# --------------------------
# Discovery
# --------------------------

def discover_inteliquent_trunk_groups(section: Section) -> Iterable[Service]:
    """
    Discover both individual and grouped trunk services.
    - Individual trunks (if not in a logical group): "trunk TrunkName"
    - Logical groups: "trunk group GroupName"
    """
    trunks = section.get("__trunks__", {})
    logical_groups = section.get("__logical_groups__", {})
    grouped_trunks = section.get("__grouped_trunks__", set())

    # Discover individual trunk services (only if not in a logical group)
    for trunk_name in sorted(trunks.keys()):
        if trunk_name not in grouped_trunks:
            yield Service(item=trunk_name)

    # Discover logical group services
    for group_name in sorted(logical_groups.keys()):
        yield Service(item=f"group {group_name}")


# --------------------------
# Check
# --------------------------

def _normalize_status(text: str) -> str:
    """Normalize status string: lowercase and remove spaces."""
    return "".join(text.lower().split())


def _get_state_value(mapping_value: Any) -> int:
    """
    Convert status mapping value to integer state value.
    Supports both integer values and string identifiers.
    """
    if isinstance(mapping_value, int):
        return mapping_value

    if isinstance(mapping_value, str):
        # Handle numeric strings (legacy support)
        if mapping_value.isdigit():
            return int(mapping_value)

        # Handle named identifiers from ruleset
        mapping = {
            "ok": 0,
            "warning": 1,
            "critical": 2,
            "unknown": 3,
        }
        return mapping.get(mapping_value.lower(), 3)  # Default to UNKNOWN

    return 3  # Default to UNKNOWN for any other type


def _check_individual_trunk(item: str, trunk_data: Dict[str, Any], params: Mapping[str, Any]) -> Iterable[Result | Metric]:
    """Check logic for individual trunk groups."""
    
    yield Result(
        state=State.OK,
        summary=f"Type: {trunk_data.get('accessType', '?')}",
        details=(
            f"Sinch trunk {trunk_data.get('customerTrunkGroupName')} in company {trunk_data.get('company', 'MISSING')}\n"
            f"features:\ne911Enabled: {trunk_data.get('e911Enabled', '?')}\nType: {trunk_data.get('accessType', '?')}"
        )
    )

    # --- Status evaluation ---
    status = trunk_data.get("status")
    if isinstance(status, str):
        norm = _normalize_status(status)
        status_mapping = params.get("status_mapping", DEFAULT_PARAMS["status_mapping"])

        # Map the normalized status to a state value
        if norm == "inservice":
            mapping_value = status_mapping.get("inservice", 0)
        elif norm == "pending":
            mapping_value = status_mapping.get("pending", 1)
        else:
            mapping_value = status_mapping.get("other", 2)

        # Convert mapping value to integer state (handles both int and string identifiers)
        state_value = _get_state_value(mapping_value)

        # Convert numeric state value to State enum
        st = State(state_value)

        yield Result(
            state=st,
            summary=f"Status: {status}",
            details=f"Status: {status}"
        )
    else:
        yield Result(
            state=State.UNKNOWN,
            summary="Status: missing",
        )
        return

    # --- Utilization evaluation & metrics ---
    # Skip utilization check for Pending trunks (utilization is null/not available)
    if _normalize_status(status) == "pending":
        return

    util = trunk_data.get("utilization") or {}
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

    utilization_levels = params.get("utilization_levels", DEFAULT_PARAMS["utilization_levels"])

    yield from check_levels(
        pcti,
        levels_upper=utilization_levels,  # SimpleLevels already returns ("fixed", (warn, crit)) format
        label="Utilization %",
        metric_name="utilization_pct",
        boundaries=(0, 100),
        render_func=lambda v: "%.1f%%" % v,
    )


def _check_logical_group(group_name: str, member_names: list, trunks: Dict[str, Dict[str, Any]], params: Mapping[str, Any]) -> Iterable[Result | Metric]:
    """Check logic for logical trunk groups - aggregates member data."""
    
    member_data = []
    for member_name in member_names:
        if member_name in trunks:
            member_data.append((member_name, trunks[member_name]))
    
    if not member_data:
        yield Result(state=State.UNKNOWN, summary="No member trunk group data found")
        return
    
    yield Result(
        state=State.OK,
        summary=f"Group contains {len(member_data)} trunk(s)",
        details=f"Members: {', '.join([m[0] for m in member_data])}"
    )

    # --- Status evaluation for group ---
    status_mapping = params.get("status_mapping", DEFAULT_PARAMS["status_mapping"])

    # Map member statuses and calculate their states
    member_statuses = []
    problem_members = []  # Members that are not "In Service"

    for member_name, member_trunk in member_data:
        status = member_trunk.get("status")
        norm_status = _normalize_status(status) if isinstance(status, str) else ""

        # Determine state value for this member
        if norm_status == "inservice":
            mapping_value = status_mapping.get("inservice", 0)
        elif norm_status == "pending":
            mapping_value = status_mapping.get("pending", 1)
        else:
            mapping_value = status_mapping.get("other", 2)

        # Convert mapping value to integer state (handles both int and string identifiers)
        state_value = _get_state_value(mapping_value)

        member_statuses.append((member_name, status, norm_status, state_value))

        if norm_status not in ("inservice",):
            problem_members.append((member_name, status))
    
    # Determine group status based on member statuses
    # Group state is the worst (highest) state among all members
    worst_state_value = max(state_value for _, _, _, state_value in member_statuses)
    group_state = State(worst_state_value)

    # Generate appropriate summary
    if not problem_members:
        group_summary = "All members In Service"
    else:
        in_service_count = sum(1 for _, _, norm_s, _ in member_statuses if norm_s == "inservice")

        if in_service_count == 0:
            problem_list = ", ".join([f"{name}({status})" for name, status in problem_members])
            group_summary = f"All members problematic: {problem_list}"
        else:
            problem_list = ", ".join([f"{name}({status})" for name, status in problem_members])
            group_summary = f"Member(s) problematic: {problem_list}"
    
    yield Result(
        state=group_state,
        summary=group_summary,
    )

    # --- Utilization aggregation ---
    total_in_calls = 0
    total_out_calls = 0
    total_capacity = 0
    has_util_data = False
    
    for member_name, member_trunk in member_data:
        status = member_trunk.get("status")
        norm_status = _normalize_status(status) if isinstance(status, str) else ""
        
        # Skip utilization for Pending members
        if norm_status == "pending":
            continue
        
        util = member_trunk.get("utilization") or {}
        in_calls = util.get("inCalls")
        out_calls = util.get("outCalls")
        capacity = util.get("capacity")
        
        if all(isinstance(v, (int, float)) for v in [in_calls, out_calls, capacity]):
            total_in_calls += in_calls
            total_out_calls += out_calls
            total_capacity += capacity
            has_util_data = True
    
    if not has_util_data or total_capacity == 0:
        yield Result(state=State.UNKNOWN, summary="Aggregated Utilization: missing or no data")
        return
    
    # Yield aggregated metrics
    yield Metric("inCalls", float(total_in_calls))
    yield Metric("outCalls", float(total_out_calls))
    yield Metric("capacity", float(total_capacity))
    
    try:
        used = float(total_in_calls) + float(total_out_calls)
        capf = float(total_capacity)
        pct = 100.0 * used / capf if capf else 0.0
        pcti = int(pct)
    except Exception:
        yield Result(state=State.UNKNOWN, summary="Aggregated Utilization: invalid values")
        return

    utilization_levels = params.get("utilization_levels", DEFAULT_PARAMS["utilization_levels"])

    yield from check_levels(
        pcti,
        levels_upper=utilization_levels,  # SimpleLevels format
        label="Aggregated Utilization %",
        metric_name="utilization_pct",
        boundaries=(0, 100),
        render_func=lambda v: "%.1f%%" % v,
    )


def check_inteliquent_trunk_groups(item: str, params: Mapping[str, Any], section: Section) -> Iterable[Result | Metric]:
    """Main check function for both individual and grouped trunk groups."""
    trunks = section.get("__trunks__", {})
    logical_groups = section.get("__logical_groups__", {})
    
    # Check if this is a logical group service
    if item.startswith("group "):
        group_name = item[len("group "):]
        if group_name not in logical_groups:
            yield Result(state=State.UNKNOWN, summary=f"Logical group '{group_name}' not found")
            return

        member_names = logical_groups[group_name]
        yield from _check_logical_group(group_name, member_names, trunks, params)
    else:
        # Check individual trunk
        if item not in trunks:
            yield Result(state=State.UNKNOWN, summary="No data for item")
            return
        
        trunk_data = trunks[item]
        yield from _check_individual_trunk(item, trunk_data, params)


# --------------------------
# Registration
# --------------------------

agent_section_inteliquent_trunks = AgentSection(
    name="inteliquent_trunks",
    parse_function=parse_inteliquent_trunk_groups,
)

check_plugin_inteliquent_trunks = CheckPlugin(
    name="inteliquent_trunks",
    service_name="trunk %s",
    discovery_function=discover_inteliquent_trunk_groups,
    check_function=check_inteliquent_trunk_groups,
    check_default_parameters=DEFAULT_PARAMS,
    check_ruleset_name="inteliquent_trunks",  # Links this check to the ruleset
)
