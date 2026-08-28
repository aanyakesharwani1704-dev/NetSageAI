from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Mapping


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    pattern: str
    root_cause: str
    osi_layer: str
    next_command: str
    fix_steps: List[str]
    base_confidence: float


RULES: List[Rule] = [
    Rule(
        rule_id="R-STP-BLOCK",
        title="Spanning-tree port stuck in blocking state",
        pattern=r"\bBLK\b|blocking state|root guard.*inconsistent",
        root_cause="Spanning Tree Protocol is blocking a port that should be forwarding.",
        osi_layer="Layer 2",
        next_command="show spanning-tree vlan <id>",
        fix_steps=[
            "configure terminal",
            "verify root bridge priority and port cost",
            "clear inconsistent state if root/loop guard triggered",
        ],
        base_confidence=0.88,
    ),
    Rule(
        rule_id="R-PORTSEC-ERRDISABLE",
        title="Port security violation (err-disabled)",
        pattern=r"err-disabled|security violation|violation count",
        root_cause="Port security violation shut the interface into err-disabled state.",
        osi_layer="Layer 2",
        next_command="show port-security interface <if>",
        fix_steps=[
            "configure terminal",
            "interface <affected-interface>",
            "shutdown",
            "no shutdown",
        ],
        base_confidence=0.93,
    ),
    Rule(
        rule_id="R-HSRP-FAIL",
        title="HSRP/FHRP standby not taking over",
        pattern=r"hsrp|standby.*state\s*init|standby.*state\s*listen|fhrp",
        root_cause="First-hop redundancy group failed to elect or fail over to an active router.",
        osi_layer="Layer 3",
        next_command="show standby brief",
        fix_steps=[
            "Verify matching HSRP group number and virtual IP on peers",
            "Check priority and preempt settings",
        ],
        base_confidence=0.85,
    ),
    Rule(
        rule_id="R-GRE-TUNNEL-DOWN",
        title="GRE tunnel down (MTU or keepalive mismatch)",
        pattern=r"tunnel\d+ is up, line protocol is down|tunnel.*keepalive|gre.*mtu mismatch",
        root_cause="GRE tunnel line protocol is down due to keepalive or MTU mismatch.",
        osi_layer="Layer 3",
        next_command="show interface tunnel <id>",
        fix_steps=[
            "Align tunnel source/destination reachability",
            "Match keepalive timers and MTU/MSS on both tunnel endpoints",
        ],
        base_confidence=0.86,
    ),
    Rule(
        rule_id="R-IPV6-RA-MISSING",
        title="IPv6 SLAAC failure due to missing router advertisement",
        pattern=r"ipv6 nd ra suppress|no ipv6 unicast-routing|slaac.*fail",
        root_cause="Router advertisements are suppressed or IPv6 routing is disabled, breaking SLAAC.",
        osi_layer="Layer 3",
        next_command="show ipv6 interface brief",
        fix_steps=[
            "configure terminal",
            "ipv6 unicast-routing",
            "no ipv6 nd ra suppress (on the client-facing interface)",
        ],
        base_confidence=0.84,
    ),
    Rule(
        rule_id="R-DHCP-SNOOP-BLOCK",
        title="DHCP snooping blocking legitimate server replies",
        pattern=r"dhcp snooping.*untrusted|option 82.*insertion fail|dhcp snooping binding",
        root_cause="DHCP snooping is dropping server-to-client replies because the uplink is untrusted.",
        osi_layer="Layer 2",
        next_command="show ip dhcp snooping",
        fix_steps=[
            "configure terminal",
            "interface <uplink-to-dhcp-server>",
            "ip dhcp snooping trust",
        ],
        base_confidence=0.87,
    ),
    Rule(
        rule_id="R-QOS-VOICE-DROP",
        title="QoS policy dropping voice/priority traffic",
        pattern=r"policy-map.*drop|class voip.*drop|priority queue.*exceed",
        root_cause="QoS policy-map is classifying and dropping latency-sensitive voice traffic.",
        osi_layer="Layer 3/4",
        next_command="show policy-map interface <if>",
        fix_steps=[
            "Review class-map match criteria for voice traffic",
            "Increase priority queue bandwidth or correct DSCP marking",
        ],
        base_confidence=0.8,
    ),
    Rule(
        rule_id="R-BGP-ASN-MISMATCH",
        title="BGP neighbor stuck in Idle/Active (AS mismatch)",
        pattern=r"bgp.*idle\b|bgp.*active\b|remote as.*mismatch|notification.*bad peer as",
        root_cause="BGP neighbor session cannot establish due to a remote-AS or peering mismatch.",
        osi_layer="Layer 3",
        next_command="show ip bgp summary",
        fix_steps=[
            "configure terminal",
            "router bgp <local-as>",
            "neighbor <ip> remote-as <correct-as>",
        ],
        base_confidence=0.9,
    ),
    Rule(
        rule_id="R-LACP-MISMATCH",
        title="EtherChannel/LACP mode mismatch",
        pattern=r"channel-misconfig|lacp.*suspended|port.*not compatible.*channel",
        root_cause="EtherChannel member ports have mismatched LACP mode and were suspended.",
        osi_layer="Layer 2",
        next_command="show etherchannel summary",
        fix_steps=[
            "Align channel-group mode (active/active or passive/active) on both ends",
            "Re-add suspended ports to the port-channel",
        ],
        base_confidence=0.91,
    ),
    Rule(
        rule_id="R-DUP-IP",
        title="Duplicate IP address conflict",
        pattern=r"duplicate address|dup_addr",
        root_cause="At least two hosts are configured with the same IP address.",
        osi_layer="Layer 3",
        next_command="show ip arp",
        fix_steps=[
            "Identify conflicting hosts",
            "Reassign a unique IP and clear stale ARP entries",
        ],
        base_confidence=0.97,
    ),
]


def _to_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _extract_evidence(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return "No direct evidence match found."
    start = max(0, match.start() - 45)
    end = min(len(text), match.end() + 90)
    snippet = text[start:end].strip()
    return " ".join(snippet.split())


def run_rule_engine(show_outputs: str) -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
    haystack = _to_text(show_outputs)

    for rule in RULES:
        if re.search(rule.pattern, haystack, flags=re.IGNORECASE):
            findings.append(
                {
                    "rule_id": rule.rule_id,
                    "title": rule.title,
                    "root_cause": rule.root_cause,
                    "osi_layer": rule.osi_layer,
                    "confidence": round(rule.base_confidence, 2),
                    "evidence": _extract_evidence(haystack, rule.pattern),
                    "next_command": rule.next_command,
                    "fix_steps": rule.fix_steps,
                }
            )

    findings.sort(key=lambda row: row["confidence"], reverse=True)
    return findings


def diagnose_with_rules(case: Mapping[str, object]) -> Dict[str, object]:
    show_outputs = _to_text(case.get("show_outputs"))
    findings = run_rule_engine(show_outputs)

    if findings:
        primary = findings[0]
        return {
            "status": "ERRORS_DETECTED",
            "primary_finding": primary,
            "findings": findings,
            "summary": f"{len(findings)} rule(s) matched. Top match: {primary['title']}",
        }

    return {
        "status": "NO_STRONG_RULE_MATCH",
        "primary_finding": {
            "rule_id": "R-NONE",
            "title": "No deterministic match",
            "root_cause": "No high-confidence deterministic signature matched this output.",
            "osi_layer": _to_text(case.get("osi_layer")) or "Unknown",
            "confidence": 0.35,
            "evidence": "No static regex rule matched the provided show_outputs.",
            "next_command": "show run",
            "fix_steps": ["Collect more evidence before remediation."],
        },
        "findings": [],
        "summary": "No deterministic signature detected; escalate to LLM inference.",
    }


def run_batch(cases: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
    output: List[Dict[str, object]] = []
    for case in cases:
        output.append(
            {
                "case_id": _to_text(case.get("case_id")),
                "checker": diagnose_with_rules(case),
            }
        )
    return output
