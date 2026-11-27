import pytest

from interior_boq import (amounts, fingerprint, line_code, option_groups, quote_totals, sqft_to_sqm, sqm_to_sqft,
                          totals)

# Sample lines with made-up rates (not real prices)
LINES = [
    {"id": "a", "room": "Kitchen", "category": "carpentry", "unit": "rft", "qty": 10, "rate": 1180, "cost_rate": 700},
    {"id": "b1", "room": "Kitchen", "category": "civil", "qty": 1, "rate": 5900, "option_group": "Top", "option_label": "A"},
    {"id": "b2", "room": "Kitchen", "category": "civil", "qty": 1, "rate": 11800, "option_group": "Top", "option_label": "B"},
    {"id": "c", "room": "Living", "category": "furniture", "qty": 1, "rate": 20000, "scope": "client"},
    {"id": "d", "room": "Living", "category": "paint", "qty": 100, "rate": 50, "status": "needs_approval"},
]


def test_amounts():
    a = amounts(LINES[0])
    assert (a["amount"], a["taxable"], a["gst"], a["cost"], a["profit"]) == (11800.0, 10000.0, 1800.0, 7000.0, 3000.0)
    assert a["margin_pct"] == 30.0


def test_totals_default_option_a():
    t = totals(LINES, with_cost=True)
    assert t["amount"] == 11800 + 5900
    assert t["options_open"] == 1 and t["pending_lines"] == 1 and t["pending_amount"] == 5000
    assert t["client_amount"] == 20000 and t["by_room"] == {"Kitchen": 17700}
    assert t["costed_lines"] == 1


def test_totals_choice_b():
    t = totals(LINES, choices={"Top": "b2"})
    assert t["amount"] == 11800 + 11800 and t["options_open"] == 0


def test_option_groups():
    g = option_groups(LINES)
    assert g[0]["group"] == "Top" and [o["id"] for o in g[0]["options"]] == ["b1", "b2"]


def test_fingerprint_changes():
    f1 = fingerprint(LINES)
    changed = [dict(LINES[0], qty=11)] + LINES[1:]
    assert f1 != fingerprint(changed)
    assert f1 == fingerprint(list(reversed(LINES)))


def test_quote_discount_before_gst():
    q = quote_totals([{"unit_price": 1180, "qty": 10, "gst_pct": 18}], discount={"pct": 10})
    assert q["taxable_before_discount"] == 10000.0 and q["discount_amount"] == 1000.0
    assert q["gst"] == 1620.0 and q["total"] == 10620 and q["cgst"] == 810.0


def test_quote_inter_state_and_cap():
    q = quote_totals([{"unit_price": 1180, "qty": 10}], discount={"pct": 50, "max_amount": 500}, intra_state=False)
    assert q["discount_amount"] == 500.0 and q["igst"] == q["gst"]


def test_line_code():
    assert line_code("carpentry", 3) == "CP-003"


def test_area_conversion():
    assert sqft_to_sqm(100) == pytest.approx(9.290304)
    assert sqm_to_sqft(1) == pytest.approx(10.7639104)
    assert sqm_to_sqft(sqft_to_sqm(1234.5)) == pytest.approx(1234.5)
    assert sqft_to_sqm(0) == 0.0 and sqft_to_sqm("50") == pytest.approx(4.645152)


def test_totals_area_in_sqft_and_sqm():
    lines = LINES + [
        {"id": "f1", "room": "Living", "category": "flooring", "unit": "sqft", "qty": 200, "rate": 118},
        {"id": "f2", "room": "Kitchen", "category": "flooring", "unit": "sqm", "qty": 10, "rate": 1180},
        {"id": "f3", "room": "Living", "category": "flooring", "unit": "sqft", "qty": 99, "rate": 1, "scope": "client"},
    ]
    t = totals(lines)
    assert t["area_sqft"] == round(200 + 10 / 0.09290304, 2) == 307.64
    assert t["area_sqm"] == round(10 + 200 * 0.09290304, 2) == 28.58
    assert t["amount"] == 11800 + 5900 + 23600 + 11800  # existing totals unchanged


def test_totals_area_zero_without_area_lines():
    t = totals(LINES)
    assert t["area_sqft"] == 0 and t["area_sqm"] == 0
