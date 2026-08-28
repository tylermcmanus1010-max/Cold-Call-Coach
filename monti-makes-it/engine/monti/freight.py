"""Freight and customs estimation.

This produces a number we can defend line by line, because it is shown to the
client — struck through — as the cost Monti is absorbing on their behalf. A
figure invented to make that gesture look bigger would be a fabricated reference
price: illegal in most of the markets we ship to, and trivially exposed the first
time a buyer asks for the breakdown. So the model here is the one a freight
forwarder actually uses.

    chargeable weight   max(actual kg, volume / dimensional divisor)
    freight             chargeable weight x lane rate, floored at a minimum
    handling            origin + destination fixed costs
    duty                declared value x the duty rate for that kind of good
    entry fees          US merchandise processing + harbour maintenance

Every component is returned, stored on the order, and rendered in the UI.
"""
import math

# Per-kg rates, USD cents, from Asia. Sea is door-to-door consolidated; air is
# express. Rates are order-of-magnitude realistic and deliberately conservative —
# an estimate we would rather undershoot than inflate.
LANE_RATES = {
    "SEA": {"per_kg": 260, "minimum": 45000, "days": 32},
    "AIR": {"per_kg": 720, "minimum": 28000, "days": 9},
}
# Destination handling, USD cents.
DESTINATION_HANDLING = {
    "United States": 18000, "Canada": 21000, "United Kingdom": 24000,
    "Australia": 26000, "Germany": 23000, "default": 25000,
}
ORIGIN_HANDLING = 12500          # export clearance, drayage to port
DIM_DIVISOR = 5000               # cm3 per kg, standard for consolidated sea/air

# Duty rate by the kind of thing it is, as a percentage of declared value.
# Approximations of the relevant HTS chapters — close enough to quote, and we
# say on the page that the broker's entry is what governs.
DUTY_RATES = {
    "Apparel & textiles": 14.9, "Bags & leather goods": 17.6,
    "Packaging & print": 0.0, "Metal & machined parts": 2.9,
    "Molded plastics": 5.3, "Injection molded plastics": 5.3,
    "Electronics & assemblies": 0.0, "Furniture & fixtures": 0.0,
    "Silicone & rubber": 3.4, "Ceramics & glass": 6.0,
    "Drinkware": 3.4, "default": 4.2,
}
# US entry fees.
MPF_PERCENT = 0.3464          # merchandise processing fee
MPF_MIN, MPF_MAX = 3231, 62670
HMF_PERCENT = 0.125           # harbour maintenance fee, sea freight only

# Rough shipped weight per unit, in grams, when we have nothing better to go on.
CATEGORY_UNIT_GRAMS = {
    "Apparel & textiles": 280, "Bags & leather goods": 620,
    "Packaging & print": 45, "Metal & machined parts": 340,
    "Molded plastics": 120, "Injection molded plastics": 120,
    "Electronics & assemblies": 260, "Furniture & fixtures": 6800,
    "Silicone & rubber": 90, "Ceramics & glass": 480, "Drinkware": 520,
    "default": 300,
}
CATEGORY_UNIT_CM3 = {
    "Apparel & textiles": 900, "Bags & leather goods": 2600,
    "Packaging & print": 260, "Metal & machined parts": 420,
    "Molded plastics": 520, "Injection molded plastics": 520,
    "Electronics & assemblies": 700, "Furniture & fixtures": 42000,
    "Silicone & rubber": 180, "Ceramics & glass": 1500, "Drinkware": 2100,
    "default": 800,
}


def _lookup(table, key):
    return table.get(key or "", table["default"])


def estimate(declared_value_cents, quantity, category=None, destination=None,
             mode="SEA", unit_grams=None, unit_cm3=None):
    """Return a full, auditable freight + customs estimate.

    `declared_value_cents` is the goods value the entry is filed on.
    """
    quantity = max(1, int(quantity or 1))
    mode = (mode or "SEA").upper()
    if mode not in LANE_RATES:
        mode = "SEA"
    lane = LANE_RATES[mode]

    grams = unit_grams if unit_grams else _lookup(CATEGORY_UNIT_GRAMS, category)
    cm3 = unit_cm3 if unit_cm3 else _lookup(CATEGORY_UNIT_CM3, category)

    actual_kg = quantity * grams / 1000.0
    volumetric_kg = quantity * cm3 / DIM_DIVISOR
    chargeable_kg = max(actual_kg, volumetric_kg)

    freight = max(lane["minimum"], int(round(chargeable_kg * lane["per_kg"])))
    handling = ORIGIN_HANDLING + _lookup(DESTINATION_HANDLING, destination)

    duty_rate = _lookup(DUTY_RATES, category)
    duty = int(round(declared_value_cents * duty_rate / 100.0))

    mpf = int(round(declared_value_cents * MPF_PERCENT / 100.0))
    mpf = min(MPF_MAX, max(MPF_MIN, mpf))
    hmf = int(round(declared_value_cents * HMF_PERCENT / 100.0)) if mode == "SEA" else 0

    freight_total = freight + handling
    customs_total = duty + mpf + hmf

    return {
        "mode": mode,
        "transit_days": lane["days"],
        "quantity": quantity,
        "unit_grams": grams,
        "unit_cm3": cm3,
        "actual_kg": round(actual_kg, 1),
        "volumetric_kg": round(volumetric_kg, 1),
        "chargeable_kg": round(chargeable_kg, 1),
        "rate_per_kg_cents": lane["per_kg"],
        "freight_cents": freight,
        "handling_cents": handling,
        "freight_total_cents": freight_total,
        "duty_rate": duty_rate,
        "duty_cents": duty,
        "mpf_cents": mpf,
        "hmf_cents": hmf,
        "customs_total_cents": customs_total,
        "grand_total_cents": freight_total + customs_total,
        "destination": destination or "your address",
    }


def breakdown_lines(est):
    """The estimate as rows, for rendering. Shown wherever the figure is shown."""
    rows = [
        (f"Chargeable weight ({est['chargeable_kg']:,.1f} kg at "
         f"${est['rate_per_kg_cents'] / 100:.2f}/kg, {est['mode'].lower()})", est["freight_cents"]),
        ("Origin and destination handling", est["handling_cents"]),
        (f"Import duty ({est['duty_rate']:g}% of declared value)", est["duty_cents"]),
        ("Merchandise processing fee", est["mpf_cents"]),
    ]
    if est["hmf_cents"]:
        rows.append(("Harbour maintenance fee", est["hmf_cents"]))
    return rows
