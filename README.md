# interior-boq

Bill of quantities (BOQ) and quote maths for home-interior projects. It's India-ready (GST-inclusive rates, CGST/SGST or IGST) and has no dependencies.

- **Line amounts**: rate × qty, with taxable value and GST worked back from GST-inclusive rates
- **A/B options**: lines can share an option group ("Kitchen top": granite A / quartz B); only the chosen line counts, and open choices are reported
- **Totals** by room and by work category, with lines awaiting approval kept apart
- **Scope**: lines you supply vs lines the client buys from their own vendor (shown as a separate estimate)
- **Cost and margin** (optional), for internal views only
- **Fingerprint** of an approved BOQ, so you can tell if anything changed after sign-off
- **Quote totals**: discount taken on the value before GST, then GST recalculated, with an optional cap for % coupons
- Standard **categories** (civil, carpentry, electrical, plumbing and more), **units** (sq ft, running ft, nos…) and **rooms**
- **Area units**: `sqft_to_sqm()` / `sqm_to_sqft()`, and totals report the area of sq ft and sq m lines in both units (`area_sqft`, `area_sqm`)

Built from the BOQ engine Hexaspace uses on real projects. **No prices are included**: bring your own rates.

## Install

```bash
pip install interior-boq
```

## Example

```python
from interior_boq import totals, quote_totals

lines = [
    {"id": "1", "room": "Kitchen", "category": "carpentry", "unit": "rft", "qty": 10, "rate": 1180, "cost_rate": 700},
    {"id": "2a", "room": "Kitchen", "category": "civil", "qty": 1, "rate": 5900, "option_group": "Top", "option_label": "A"},
    {"id": "2b", "room": "Kitchen", "category": "civil", "qty": 1, "rate": 11800, "option_group": "Top", "option_label": "B"},
]
totals(lines, with_cost=True, choices={"Top": "2b"})
# {'amount': 23600, 'taxable': 20000.0, 'gst': 3600.0, 'by_room': {'Kitchen': 23600}, 'margin_pct': 30.0, ...}

quote_totals([{"unit_price": 1180, "qty": 10}], discount={"pct": 10}, intra_state=True)
# discount on taxable value, GST recalculated: total 10620, cgst 810, sgst 810
```

Rates in the examples are made up.

## Roadmap

- Area-based quick estimates (carpet area → BOQ starter)
- Export to Excel and PDF
- Change orders (variations after sign-off)

Pull requests are welcome: see issues labelled `good first issue`.

## Licence

MIT. Maintained by [Hexaspace](https://hexaspace.in).
