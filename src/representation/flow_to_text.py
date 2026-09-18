from __future__ import annotations

import math
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Mapping, Sequence

EXCLUDED_COLUMNS = {"Seq", "SrcTCPBase", "DstTCPBase", "CategoryLabel"}

PROTOCOL_COLUMNS = [
    "Proto_arp",
    "Proto_icmp",
    "Proto_ipv6-icmp",
    "Proto_tcp",
    "Proto_udp",
]

FLAG_COLUMNS = [
    "Flgs_e",
    "Flgs_e_*",
    "Flgs_e_d",
    "Flgs_e_g",
    "Flgs_e_r",
    "Flgs_e_s",
    "Flgs_eU",
]

STATE_COLUMNS = [
    "State_CLO",
    "State_CON",
    "State_ECO",
    "State_FIN",
    "State_INT",
    "State_NRS",
    "State_REQ",
    "State_RSP",
    "State_RST",
    "State_TST",
    "State_URH",
    "State_URHPRO",
]

PROTOCOL_LABELS = {
    "Proto_arp": "ARP",
    "Proto_icmp": "ICMP",
    "Proto_ipv6-icmp": "IPv6-ICMP",
    "Proto_tcp": "TCP",
    "Proto_udp": "UDP",
}

FLAG_LABELS = {
    "Flgs_e": "e",
    "Flgs_e_*": "e_*",
    "Flgs_e_d": "e_d",
    "Flgs_e_g": "e_g",
    "Flgs_e_r": "e_r",
    "Flgs_e_s": "e_s",
    "Flgs_eU": "eU",
}

FLAG_PRIORITY = {
    "e": 0,
    "e_s": 1,
    "e_r": 2,
    "e_d": 3,
    "e_g": 4,
    "e_*": 5,
    "eU": 6,
}

STATE_LABELS = {
    "State_CLO": "CLO",
    "State_CON": "CON",
    "State_ECO": "ECO",
    "State_FIN": "FIN",
    "State_INT": "INT",
    "State_NRS": "NRS",
    "State_REQ": "REQ",
    "State_RSP": "RSP",
    "State_RST": "RST",
    "State_TST": "TST",
    "State_URH": "URH",
    "State_URHPRO": "URHPRO",
}

FLOW_GROUPS: "OrderedDict[str, List[str]]" = OrderedDict(
    [
        ("Traffic volume", [
            "TotPkts",
            "TotBytes",
            "TotAppByte",
            "SrcPkts",
            "DstPkts",
            "SrcBytes",
            "DstBytes",
            "SAppBytes",
            "DAppBytes",
        ]),
        ("Packet characteristics", [
            "sMeanPktSz",
            "dMeanPktSz",
            "sMinPktSz",
            "dMinPktSz",
            "sMaxPktSz",
            "dMaxPktSz",
            "Mean",
            "Min",
            "Max",
            "Sum",
        ]),
        ("Traffic rates and load", [
            "Rate",
            "SrcRate",
            "DstRate",
            "Load",
            "SrcLoad",
            "DstLoad",
        ]),
        ("Loss", [
            "SrcLoss",
            "DstLoss",
            "Loss",
            "pLoss",
        ]),
        ("Timing", [
            "DIntPktAct",
            "SIntPktAct",
            "DIntPkt",
            "SIntPkt",
            "DIntPktMin",
            "DIntPktMax",
            "SIntPktMin",
            "SIntPktMax",
            "SIntPktIdl",
            "SrcJitter",
            "TcpRtt",
        ]),
        ("TCP/connection characteristics", [
            "DstWin",
            "SrcWin",
            "SynAck",
            "AckDat",
            "sTos",
            "sTtl",
            "sHops",
            "PCRatio",
        ]),
    ]
)

FIELD_LABELS = {
    "TotPkts": "Total packets",
    "TotBytes": "Total bytes",
    "TotAppByte": "Application bytes",
    "SrcPkts": "Source packets",
    "DstPkts": "Destination packets",
    "SrcBytes": "Source bytes",
    "DstBytes": "Destination bytes",
    "SAppBytes": "Source application bytes",
    "DAppBytes": "Destination application bytes",
    "sMeanPktSz": "Source mean packet size",
    "dMeanPktSz": "Destination mean packet size",
    "sMinPktSz": "Source minimum packet size",
    "dMinPktSz": "Destination minimum packet size",
    "sMaxPktSz": "Source maximum packet size",
    "dMaxPktSz": "Destination maximum packet size",
    "Mean": "Mean",
    "Min": "Minimum",
    "Max": "Maximum",
    "Sum": "Sum",
    "Rate": "Rate",
    "SrcRate": "Source rate",
    "DstRate": "Destination rate",
    "Load": "Load",
    "SrcLoad": "Source load",
    "DstLoad": "Destination load",
    "SrcLoss": "Source loss",
    "DstLoss": "Destination loss",
    "Loss": "Loss",
    "pLoss": "Packet loss percent",
    "DIntPktAct": "Destination inter-packet activity",
    "SIntPktAct": "Source inter-packet activity",
    "DIntPkt": "Destination inter-packet interval",
    "SIntPkt": "Source inter-packet interval",
    "DIntPktMin": "Destination inter-packet minimum",
    "DIntPktMax": "Destination inter-packet maximum",
    "SIntPktMin": "Source inter-packet minimum",
    "SIntPktMax": "Source inter-packet maximum",
    "SIntPktIdl": "Source inter-packet idle time",
    "SrcJitter": "Source jitter",
    "TcpRtt": "TCP round trip time",
    "DstWin": "Destination window",
    "SrcWin": "Source window",
    "SynAck": "SYN/ACK",
    "AckDat": "ACK data",
    "sTos": "Source ToS",
    "sTtl": "Source TTL",
    "sHops": "Source hops",
    "PCRatio": "Packet count ratio",
}


def _coerce_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "t", "yes", "y"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "", "nan", "none", "null"}:
            return False
        return False
    if isinstance(value, (bool, int, float)) and not isinstance(value, bool):
        if math.isnan(float(value)):
            return False
        return bool(value)
    return bool(value)


def _format_number(value: Any) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            if math.isnan(value):
                return "nan"
            if math.isinf(value):
                return "inf" if value > 0 else "-inf"
            if value.is_integer():
                return str(int(value))
            return format(value, ".6f").rstrip("0").rstrip(".")
        return str(value)
    return str(value)


def protocol_from_row(row: Mapping[str, Any]) -> str:
    active = []
    for col in PROTOCOL_COLUMNS:
        if _coerce_bool(row.get(col, False)):
            active.append(PROTOCOL_LABELS.get(col, col))
    if not active:
        return "unknown"
    if len(active) == 1:
        return active[0]
    return ", ".join(active)


def active_flags(row: Mapping[str, Any]) -> str:
    active = []
    for col in FLAG_COLUMNS:
        if _coerce_bool(row.get(col, False)):
            active.append(FLAG_LABELS.get(col, col))
    if not active:
        return "none"
    return ", ".join(sorted(active, key=lambda value: FLAG_PRIORITY.get(value, 99)))


def active_states(row: Mapping[str, Any]) -> str:
    active = []
    for col in STATE_COLUMNS:
        if _coerce_bool(row.get(col, False)):
            active.append(STATE_LABELS.get(col, col))
    if not active:
        return "none"
    return ", ".join(active)


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if hasattr(value, "item"):
        try:
            return _serialize_value(value.item())
        except Exception:
            pass
    return str(value)


def _section_lines(row: Mapping[str, Any], section_name: str, fields: Sequence[str]) -> List[str]:
    lines = [f"{section_name}:"]
    for field in fields:
        value = row.get(field)
        if value is None:
            continue
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            continue
        lines.append(f"- {FIELD_LABELS.get(field, field)}: {_format_number(value)}")
    return lines


def row_to_text(row: Mapping[str, Any]) -> str:
    protocol = protocol_from_row(row)
    sport_value = row.get("Sport")
    dport_value = row.get("Dport")

    lines: List[str] = [
        "Network flow:",
        f"- Protocol: {protocol}",
        f"- Source port: {_format_number(sport_value)}",
        f"- Destination port: {_format_number(dport_value)}",
        "",
    ]

    for section_name, fields in FLOW_GROUPS.items():
        section_lines = _section_lines(row, section_name, fields)
        if len(section_lines) > 1:
            lines.extend(section_lines)
            lines.append("")

    lines.append("Connection behavior:")
    lines.append(f"- Active flow flags: {active_flags(row)}")
    lines.append(f"- Connection states: {active_states(row)}")
    return "\n".join(lines).rstrip()


def row_to_record(row: Mapping[str, Any], split_name: str, row_index: int) -> Dict[str, Any]:
    label = row.get("CategoryLabel")
    protocol = protocol_from_row(row)
    sport = row.get("Sport")
    dport = row.get("Dport")
    flow_id = f"{split_name}_{row_index:08d}"

    metadata = {
        "flow_id": flow_id,
        "CategoryLabel": _serialize_value(label),
        "protocol": protocol,
        "Sport": _serialize_value(sport),
        "Dport": _serialize_value(dport),
        "features": {},
    }

    for key, value in row.items():
        if key in EXCLUDED_COLUMNS:
            continue
        metadata["features"][key] = _serialize_value(value)

    return {
        "id": flow_id,
        "text": row_to_text(row),
        "label": _serialize_value(label),
        "metadata": metadata,
    }
