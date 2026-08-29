"""CHG-001, the clause that is not about colour: "Marks sum to the headline total."

Run against a database with orders in it. The launched build has none, so this uses
the throwaway seeded database (§1.5's explicitly labelled local development seed):

    DATABASE_PATH=/tmp/seeded.db PYTHONPATH=. python series-arithmetic-probe.py
"""
from datetime import timedelta
from monti import create_app
import monti.analytics as A
from monti.utils import utcnow, parse

app = create_app()
print("# CHG-001 — do the marks sum to the headline?")
print()
print("`_window(days)` returns (utcnow() - days, utcnow()) — both carrying a time of day.")
print("The SQL sums every PAID order in [start, end). The bucket loop then starts at")
print("parse(start) and emits exactly `days` buckets, one per calendar date.")
print()
with app.app_context():
    print(f"{'period':7} {'headline':>14} {'marks sum':>14} {'gap':>13} {'points':>7}  buckets")
    print("-" * 92)
    for period, days, _ in A.PERIODS:
        if days == 1:
            continue
        head = A.summary(period)["revenue"]
        pts = A.series(period)["points"]
        marks = sum(p["revenue"] for p in pts)
        keys = [p["label"] for p in pts]
        span = f"{keys[0]} .. {keys[-1]}" if keys else "-"
        print(f"{period:7} {head:>14,} {marks:>14,} {head - marks:>13,} {len(pts):>7}  {span}")

    print()
    start, end = A._window(7)
    print(f"For 7d:  SQL window  [{start}, {end})")
    print(f"         buckets     {parse(start).strftime('%b %-d')} .. "
          f"{(parse(start) + timedelta(days=6)).strftime('%b %-d')}")
    print(f"         today is    {utcnow().strftime('%b %-d')}")
    print()
    print("Two defects in one loop:")
    print()
    print("  1. TODAY IS NEVER DRAWN. The window ends at utcnow(), so today's orders are")
    print("     inside the SQL result and inside the headline. The loop emits `days`")
    print("     buckets starting from the window's start date, which lands on yesterday.")
    print("     Today's revenue is counted in the total and has no bar.")
    print()
    print("  2. THE OLDEST BAR IS A PARTIAL DAY, DRAWN AS A WHOLE ONE. The window starts")
    print("     mid-afternoon seven days ago, so the first bucket holds only part of that")
    print("     date's revenue and is rendered the same height a full day would be.")
    print()
    print("CHG-001's gate: 'Marks sum to the headline total.' They do not, at any period.")
    print("VIZ-01's charter: 'Every chart that represents a period must reconcile to the")
    print("ledger for that period. A chart that disagrees with the ledger is a P0")
    print("regardless of how it looks.' This one disagrees with its own headline.")
    print()
    print("This is independent of the black fill. Fixing the stylesheet leaves it intact.")
