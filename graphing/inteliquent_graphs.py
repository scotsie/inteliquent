#!/usr/bin/env python3
# Graphs for Inteliquent trunk groups (Checkmk 2.3+)

from cmk.graphing.v1 import Title
from cmk.graphing.v1.graphs import Graph
from cmk.graphing.v1.metrics import (
    Color,
    DecimalNotation,
    Metric,
    Unit
)
from cmk.graphing.v1.perfometers import (
    Perfometer,
    FocusRange,
    Closed
)


# Define units
unit_percentage = Unit(DecimalNotation("%"))
unit_count = Unit(DecimalNotation(""))


metric_incalls = Metric(
    name="inCalls",
    title=Title("Inbound Calls"),
    unit=unit_count,
    color=Color.BLUE
)


metric_outcalls = Metric(
    name="outCalls",
    title=Title("Outbound Calls"),
    unit=unit_count,
    color=Color.GREEN
)


metric_capacity = Metric(
    name="capacity",
    title=Title("Capacity"),
    unit=unit_count,
    color=Color.LIGHT_RED
)


metric_utilization_pct = Metric(
    name="utilization_pct",
    title=Title("Utilization"),
    unit=unit_percentage,
    color=Color.GREEN
)


#metric_active_sessions = Metric(
#    name="active_sessions",
#    title=Title("Active Sessions"),
#    unit=unit_count,
#    color=Color.GREEN
#)


graph_trunk_utilization = Graph(
    name="inteliquent_trunk_utilization",
    title=Title("Trunk Utilization"),
    compound_lines=[
        "inCalls",
        "outCalls"
    ],
    simple_lines=[
        "capacity"
    ]
)


perfometer_trunk_utilization_pct = Perfometer(
    name="utilization_pct",
    focus_range=FocusRange(
        lower=Closed(0),
        upper=Closed(100),
    ),
    segments=["utilization_pct"],
)
