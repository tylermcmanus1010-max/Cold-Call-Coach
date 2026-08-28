"""The Decision Room — three ways to buy the same part (Appendix E.1, §3.2 DR-*).

The surface that replaced the single flat quote. Two rails, three strategies,
and a set of controls that recompute everything downstream — and the whole thing
is a projection of numbers an admin entered on the pricing desk.

The rule that shapes this module is §11.1: **every number a client sees traces
to a stored admin input with a publish timestamp.** Nothing here is a literal.
The six cost inputs, the freight lanes, the per-strategy extras, the lever
savings — each is a row someone entered and published, and `provenance()` walks
a rendered figure back to the input ids behind it so `A15` can assert it.

Two consequences that look like restrictions and are the point:

  No extrapolation.   `quantity_bounds()` reads the entered band. A slider that
                      lets a client drag past the quantities the desk priced
                      would be inventing a price at the far end, which §11.1
                      forbids outright. Appendix B is emphatic that the bounds
                      are a data field and not a hard-coded 1,000-10,000 —
                      at $0.14 a container that range is a $140 order.

  No unpriced lever.  A lever with no entered saving is not offered. The
                      "what would need to change" panel exists to tell a client
                      what a change is worth, and a number we guessed is worse
                      than an absent row.
"""
from .db import query

# The six cost inputs the desk enters per item (E5.03). Named and fixed, not
# free-form: a seventh input nobody agreed on is how a price stops being
# explainable.
COST_FIELDS = ("material_unit", "tooling_total", "packaging_custom_unit",
               "packaging_standard_unit", "duty_rate_pct", "lab_total")

COST_LABELS = {
    "material_unit": "Material + labour, per unit",
    "tooling_total": "Tooling, total",
    "packaging_custom_unit": "Custom packaging, per unit",
    "packaging_standard_unit": "Standard packaging, per unit",
    "duty_rate_pct": "Duty rate",
    "lab_total": "Certification lab, total",
}

STRATEGY_SLOTS = [
    (0, "Lowest landed cost", "amortized"),
    (1, "Fastest arrival", "upfront"),
    (2, "Highest certainty", "upfront_with_sample"),
]


# --------------------------------------------------------------------------
# reading the entered numbers
# --------------------------------------------------------------------------
def cost_inputs(item_id, published_only=True):
    """The six inputs for an item, as {field: {value, input_id, entered_by, published_at}}.

    `published_only` defaults True and is the gate §11.1 asks for: an entered
    but unpublished number is invisible to every member-facing caller, because
    the filter is here rather than at each of them.
    """
    sql = ("SELECT * FROM pricing_inputs WHERE item_id = ? AND field IN "
           "(" + ",".join("?" * len(COST_FIELDS)) + ")")
    args = [item_id, *COST_FIELDS]
    if published_only:
        sql += " AND published_at IS NOT NULL"
    rows = query(sql + " ORDER BY id", tuple(args))

    out = {}
    for row in rows:                       # later rows win; the newest publish stands
        out[row["field"]] = {
            "value_cents": row["value_cents"],
            "input_id": row["id"],
            "entered_by": row["entered_by"],
            "published_at": row["published_at"],
        }
    return out


def lanes():
    """Freight lanes, keyed by mode. Admin inputs, not constants."""
    return {r["mode"]: r for r in query("SELECT * FROM freight_lanes ORDER BY id")}


def strategies(item_id):
    return query("SELECT * FROM item_strategies WHERE item_id = ? ORDER BY slot", (item_id,))


def levers(item_id):
    return query("SELECT * FROM item_levers WHERE item_id = ? AND active = 1 ORDER BY id",
                 (item_id,))


def quantity_bounds(item):
    """The slider's range, from entered data (Appendix B / E1.05, E.7).

    Preference order: the item's own band, then the published price matrix's
    tiers, then nothing. Returning None is a real answer — it means no quantity
    was priced, and the caller shows the item without a slider rather than
    inventing a range to drag along.
    """
    if item["qty_min"] and item["qty_max"]:
        return {"min": item["qty_min"], "max": item["qty_max"],
                "step": item["qty_step"], "source": "entered on the item"}

    if item["catalog_item_id"]:
        band = query(
            "SELECT MIN(c.quantity_min) AS lo, MAX(COALESCE(c.quantity_max, c.quantity_min)) AS hi "
            "FROM price_matrix_cells c JOIN price_matrices m ON m.id = c.matrix_id "
            "WHERE m.item_id = ? AND m.published_at IS NOT NULL", (item["catalog_item_id"],),
            one=True)
        if band and band["lo"]:
            return {"min": band["lo"], "max": band["hi"], "step": item["qty_step"],
                    "source": "the published price matrix"}
    return None


# --------------------------------------------------------------------------
# the arithmetic
# --------------------------------------------------------------------------
def ex_works(costs, quantity, *, amortize_tooling=True, extra_cents=0,
             standard_packaging=False, spec_saving_cents=0, include_lab=False):
    """Per-unit ex-works, in cents, with the input ids that produced it.

    Returns (cents, [input_id, ...]) rather than a bare number so the caller can
    carry provenance through to the rendered field — §11.1's requirement is that
    the *rendered* figure resolves to inputs, which only works if the arithmetic
    hands them along.
    """
    used = []

    def take(field):
        entry = costs.get(field)
        if entry is None:
            return None
        used.append(entry["input_id"])
        return entry["value_cents"]

    material = take("material_unit")
    if material is None:
        return None, []

    packaging = take("packaging_standard_unit" if standard_packaging
                     else "packaging_custom_unit") or 0

    total = material - spec_saving_cents + packaging + extra_cents

    if amortize_tooling:
        tooling = take("tooling_total")
        if tooling and quantity:
            total += tooling / quantity

    if include_lab:
        lab = take("lab_total")
        if lab and quantity:
            total += lab / quantity

    return total, used


def freight_unit(mode, quantity, lane_rows):
    """Per-unit freight for a lane at this quantity, and the lane row behind it."""
    lane = lane_rows.get(mode)
    if lane is None or not quantity:
        return None, None
    return lane["per_unit_cents"] + lane["fixed_cents"] / quantity, lane


def landed(costs, lane_rows, quantity, mode, **kw):
    """Landed per unit: ex-works, plus freight, plus duty on the ex-works value.

    Duty applies to the ex-works value rather than the landed one, which is how
    a customs entry actually computes it — charging duty on freight would
    overstate every figure on the page by a few percent, consistently, in our
    favour.
    """
    ex, used = ex_works(costs, quantity, **kw)
    if ex is None:
        return None
    fr, lane = freight_unit(mode, quantity, lane_rows)
    if fr is None:
        return None
    duty_entry = costs.get("duty_rate_pct")
    duty_rate = (duty_entry["value_cents"] / 100.0) if duty_entry else 0.0
    if duty_entry:
        used.append(duty_entry["input_id"])
    duty = ex * duty_rate / 100.0
    return {
        "ex_works_cents": ex,
        "freight_cents": fr,
        "duty_cents": duty,
        "landed_cents": ex + fr + duty,
        "input_ids": used,
        "lane": lane,
    }


def strategy_view(item, strat, costs, lane_rows, quantity, mode_override=None,
                  tooling_treatment=None):
    """One strategy card's numbers.

    A strategy pins its own freight mode when the route requires it — "fastest
    arrival" is an air route and does not become an ocean route because the
    client moved the selector. The selector governs the routes that are free to
    move.
    """
    mode = strat["mode"] if strat["mode"] == "air" else (mode_override or strat["mode"])
    treatment = tooling_treatment or strat["tooling_treatment"]

    figures = landed(costs, lane_rows, quantity, mode,
                     amortize_tooling=(treatment == "amortized"),
                     extra_cents=strat["extra_cents"],
                     include_lab=bool(strat["includes_lab"]))
    if figures is None:
        return None

    order_total = figures["landed_cents"] * quantity
    if treatment != "amortized":
        tooling = costs.get("tooling_total")
        if tooling:
            order_total += tooling["value_cents"]

    return {
        "slot": strat["slot"],
        "label": strat["label"],
        "title": strat["title"],
        "lead_days": strat["lead_days"],
        "production": strat["production"],
        "inspection": strat["inspection"],
        "footnote": strat["footnote"],
        "mode": mode,
        "treatment": treatment,
        "order_total_cents": order_total,
        **figures,
    }


def lever_savings(item, costs, lane_rows, quantity, mode, tooling_treatment,
                  bounds=None):
    """What each offered lever is worth, priced independently (E1.11).

    A quantity lever prices itself off the entered band — and refuses to price
    itself past the top of it, because a saving at a quantity nobody quoted is
    an extrapolation.
    """
    base = landed(costs, lane_rows, quantity, mode,
                  amortize_tooling=(tooling_treatment == "amortized"))
    if base is None:
        return []

    out = []
    for lever in levers(item["id"]):
        if lever["kind"] == "qty":
            step_to = _next_tier(quantity, bounds)
            if step_to is None:
                continue                    # nothing left inside the entered band
            alt = landed(costs, lane_rows, step_to, mode,
                         amortize_tooling=(tooling_treatment == "amortized"))
            saving = base["landed_cents"] - alt["landed_cents"] if alt else 0
            out.append({**dict(lever), "saving": max(0, saving), "quantity_to": step_to,
                        "label_rendered": lever["label"]
                        .replace("QTYNEW", f"{step_to:,}")
                        .replace("QTYNOW", f"{quantity:,}")})
            continue

        kw = {"standard_packaging": True} if lever["kind"] == "pkg" else {
            "spec_saving_cents": lever["saving_cents"]}
        alt = landed(costs, lane_rows, quantity, mode,
                     amortize_tooling=(tooling_treatment == "amortized"), **kw)
        saving = base["landed_cents"] - alt["landed_cents"] if alt else 0
        out.append({**dict(lever), "saving": max(0, saving), "quantity_to": None,
                    "label_rendered": lever["label"]})
    return out


def _next_tier(quantity, bounds):
    """The next quantity worth offering, inside the entered band."""
    if not bounds:
        return None
    step = max(bounds["step"], (bounds["max"] - bounds["min"]) // 5 or 1)
    nxt = quantity + step
    return nxt if nxt <= bounds["max"] else None


def engineered_price(item, costs, lane_rows, quantity, mode, tooling_treatment,
                     chosen_kinds, bounds=None):
    """Where the price lands once the ticked levers are applied together."""
    chosen = [l for l in lever_savings(item, costs, lane_rows, quantity, mode,
                                       tooling_treatment, bounds)
              if l["kind"] in chosen_kinds]
    final_qty = quantity
    kw = {}
    for lever in chosen:
        if lever["kind"] == "qty" and lever["quantity_to"]:
            final_qty = lever["quantity_to"]
        elif lever["kind"] == "pkg":
            kw["standard_packaging"] = True
        elif lever["kind"] == "spec":
            kw["spec_saving_cents"] = lever["saving_cents"]

    figures = landed(costs, lane_rows, final_qty, mode,
                     amortize_tooling=(tooling_treatment == "amortized"), **kw)
    return {"quantity": final_qty, "chosen": chosen,
            "landed_cents": figures["landed_cents"] if figures else None}


def freight_comparison(costs, lane_rows, quantity, tooling_treatment):
    """Every lane at this quantity, so the table and the cards cannot disagree —
    both read the same `landed()` over the same inputs (E1.12)."""
    rows = []
    for mode, lane in lane_rows.items():
        figures = landed(costs, lane_rows, quantity, mode,
                         amortize_tooling=(tooling_treatment == "amortized"))
        if figures is None:
            continue
        rows.append({
            "mode": mode,
            "lane_label": lane["lane_label"],
            "transit_label": lane["transit_label"],
            "freight_unit_cents": figures["freight_cents"],
            "freight_total_cents": figures["freight_cents"] * quantity,
            "landed_cents": figures["landed_cents"],
        })
    return rows


def price_curve(costs, lane_rows, bounds, mode="ocean", tooling_treatment="amortized"):
    """The quantity curve, sampled only inside the entered band (E3.03, E3.04).

    The chart and the table are built from this one list, so the two can never
    disagree about the same point — E3.04 requires exactly that, and the way to
    get it is not to compute the curve twice.
    """
    if not bounds:
        return []
    lo, hi = bounds["min"], bounds["max"]
    points = sorted({lo, *[lo + (hi - lo) * n // 4 for n in range(1, 4)], hi})
    curve = []
    for qty in points:
        figures = landed(costs, lane_rows, qty, mode,
                         amortize_tooling=(tooling_treatment == "amortized"))
        if figures is None:
            continue
        curve.append({
            "quantity": qty,
            "ex_works_cents": figures["ex_works_cents"],
            "landed_cents": figures["landed_cents"],
            "order_total_cents": figures["landed_cents"] * qty,
            "interpolated": qty not in (lo, hi),
        })
    return curve


# --------------------------------------------------------------------------
# provenance (§11.1, A15)
# --------------------------------------------------------------------------
def provenance(item_id):
    """Every figure this item can render, and the input ids behind it.

    What `A15` walks. A field that appears here with an empty `input_ids` is a
    number with nothing behind it, which is a P1 — so the check reads this
    rather than trusting that the arithmetic remembered.
    """
    item = query("SELECT * FROM decision_items WHERE id = ?", (item_id,), one=True)
    if item is None or not item["published_at"]:
        return {"item_id": item_id, "published": False, "fields": []}

    costs = cost_inputs(item_id)
    lane_rows = lanes()
    bounds = quantity_bounds(item)
    qty = bounds["min"] if bounds else 0

    fields = []
    for strat in strategies(item_id):
        view = strategy_view(item, strat, costs, lane_rows, qty)
        if view is None:
            fields.append({"field": f"strategy {strat['slot']}", "input_ids": [],
                           "note": "renders no figure — inputs missing"})
            continue
        for name in ("ex_works_cents", "freight_cents", "duty_cents",
                     "landed_cents", "order_total_cents"):
            fields.append({
                "field": f"strategy {strat['slot']}.{name}",
                "value": view[name],
                "input_ids": sorted(set(view["input_ids"])),
                "lane_id": view["lane"]["id"] if view["lane"] else None,
            })
    return {"item_id": item_id, "ref": item["ref"], "published": True,
            "published_at": item["published_at"], "fields": fields}
