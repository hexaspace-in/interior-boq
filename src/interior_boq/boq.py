"""BOQ maths: line amounts (GST-inclusive rates), option groups (A/B choices), totals by room and
category, supplier vs client-bought scope, optional cost and margin, and a fingerprint of what was approved.

A line is a plain dict::

    {"id": "l1", "room": "Kitchen", "category": "carpentry", "name": "Base units, BWP + laminate",
     "unit": "rft", "qty": 10, "rate": 4500,          # rate includes GST
     "gst_pct": 18, "cost_rate": 3000,                # optional, cost without GST
     "status": "ok",                                  # only "ok" lines count; e.g. "needs_approval" do not
     "scope": "supplier",                             # "supplier" (you supply) or "client" (client buys)
     "option_group": "Kitchen top", "option_label": "A"}   # optional A/B options
"""
import hashlib
import json
from typing import Dict, List, Optional

from .catalog import DEFAULT_GST, sqft_to_sqm, sqm_to_sqft

Choices = Dict[str, str]  # option_group -> chosen line id


def amounts(line: dict) -> dict:
    """Amount (incl. GST), taxable value, GST, and if cost_rate is given: cost, profit, margin %."""
    g = float(line.get("gst_pct") or DEFAULT_GST)
    amount = round(float(line.get("rate") or 0) * float(line.get("qty") or 0), 2)
    taxable = round(amount / (1 + g / 100), 2)
    cost = round(float(line["cost_rate"]) * float(line["qty"]), 2) if line.get("cost_rate") is not None else None
    return {"amount": amount, "taxable": taxable, "gst": round(amount - taxable, 2), "cost": cost,
            "profit": round(taxable - cost, 2) if cost is not None else None,
            "margin_pct": round((taxable - cost) / taxable * 100, 1) if cost is not None and taxable else None}


def counted(lines: List[dict], choices: Optional[Choices] = None) -> List[dict]:
    """Lines that count: status ok; within an option group only the chosen line (else the first by label)."""
    choices = choices or {}
    ok = [l for l in lines if l.get("status", "ok") == "ok"]
    first: Dict[str, str] = {}
    for l in sorted([l for l in ok if l.get("option_group")], key=lambda l: l.get("option_label") or ""):
        first.setdefault(l["option_group"], l["id"])
    return [l for l in ok if not l.get("option_group") or choices.get(l["option_group"], first[l["option_group"]]) == l["id"]]


def option_groups(lines: List[dict], choices: Optional[Choices] = None) -> List[dict]:
    choices, out = choices or {}, {}
    for l in lines:
        if l.get("status", "ok") == "ok" and l.get("option_group"):
            out.setdefault(l["option_group"], []).append(l)
    return [{"group": g, "chosen": choices.get(g), "options": sorted(ls, key=lambda l: l.get("option_label") or "")}
            for g, ls in out.items()]


def is_supplier_line(line: dict) -> bool:
    return (line.get("scope") or "supplier") == "supplier"


def totals(lines: List[dict], with_cost: bool = False, choices: Optional[Choices] = None) -> dict:
    """Totals of supplier lines; client-bought lines are reported apart as an estimate.

    area_sqft / area_sqm: total qty of supplier lines measured in sq ft or sq m, in both units."""
    everything = counted(lines, choices)
    live = [l for l in everything if is_supplier_line(l)]
    theirs = [l for l in everything if not is_supplier_line(l)]
    groups = option_groups(lines, choices)
    t = {"lines": len(live), "amount": 0.0, "taxable": 0.0, "gst": 0.0,
         "option_groups": len(groups), "options_open": sum(1 for g in groups if not g["chosen"]),
         "pending_lines": sum(1 for l in lines if l.get("status", "ok") != "ok"),
         "pending_amount": round(sum(amounts(l)["amount"] for l in lines if l.get("status", "ok") != "ok"), 2)}
    costed = 0
    cost = taxable_costed = 0.0
    for l in live:
        a = amounts(l)
        t["amount"] += a["amount"]; t["taxable"] += a["taxable"]; t["gst"] += a["gst"]
        if a["cost"] is not None:
            costed += 1; cost += a["cost"]; taxable_costed += a["taxable"]
    t = {k: round(v, 2) if isinstance(v, float) else v for k, v in t.items()}
    t["amount"] = round(t["amount"])
    t["by_room"], t["by_category"] = {}, {}
    for l in live:
        a = amounts(l)["amount"]
        room, cat = l.get("room") or "Whole home", l.get("category") or "other"
        t["by_room"][room] = round(t["by_room"].get(room, 0) + a)
        t["by_category"][cat] = round(t["by_category"].get(cat, 0) + a)
    sqft = sum(float(l.get("qty") or 0) for l in live if l.get("unit") == "sqft")
    sqm = sum(float(l.get("qty") or 0) for l in live if l.get("unit") == "sqm")
    t["area_sqft"] = round(sqft + sqm_to_sqft(sqm), 2)
    t["area_sqm"] = round(sqm + sqft_to_sqm(sqft), 2)
    t["client_amount"] = round(sum(amounts(l)["amount"] for l in theirs))
    t["client_lines"] = len(theirs)
    if with_cost:
        t.update(cost=round(cost, 2), profit=round(taxable_costed - cost, 2), costed_lines=costed,
                 margin_pct=round((taxable_costed - cost) / taxable_costed * 100, 1) if taxable_costed else None)
    return t


def fingerprint(lines: List[dict], choices: Optional[Choices] = None) -> str:
    """Stable hash of what an approver saw. Any change to qty, rate, spec, room, scope, GST or option picks changes it."""
    rows = sorted([[l["id"], float(l.get("qty") or 0), float(l.get("rate") or 0), l.get("spec") or {}, l.get("room"),
                    l.get("scope") or "supplier", float(l.get("gst_pct") or DEFAULT_GST), l.get("option_group")]
                   for l in lines if l.get("status", "ok") == "ok"], key=lambda r: r[0])
    ch = {g: c for g, c in sorted((choices or {}).items())}
    return hashlib.sha256(json.dumps([rows, ch], sort_keys=True, default=str).encode()).hexdigest()[:32]
