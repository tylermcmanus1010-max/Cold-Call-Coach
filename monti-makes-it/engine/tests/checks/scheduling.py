"""A40 — the consultation calendar offers nothing it cannot honour.

A booking page has two ways to lie, and both look fine on screen.

  It offers a time nobody agreed to.   The nine-to-five grid. The applicant
  picks 4pm Friday, nobody joins, and the first anyone knows is the empty call.
  §1.5 calls this fixture data on a client-facing surface, and a calendar is the
  purest example: every cell is a promise.

  It offers the same time twice.       Two people load the page, both see 10:00,
  both click. A read-then-write check passes for both, because the gap between
  reading and writing is exactly as long as it takes to render a page.

So this check holds four properties:

  Provenance.   Every offered slot falls inside a window an admin entered, on
                the right weekday, at the right local time in that window's own
                timezone. Not "some slots look plausible" — each one is walked
                back to the row it came from.

  Subtraction.  A booked slot, a blacked-out range, and anything inside the lead
                time are all absent from the next offer.

  Uniqueness.   Booking the same slot twice fails. Tested by actually doing it,
                because the guarantee lives in a UNIQUE index and an index is
                the only thing that holds when two requests interleave.

  The door.     POST /apply with a slot that was never offered must not book it.
                A picker produces a value; it does not authorise it.

The daylight-saving property is checked too, and it is not decoration: a window
stored as a UTC offset silently moves an hour twice a year, and the person who
finds out is the applicant sitting on a call alone.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import Check, Finding

FMT = "%Y-%m-%d %H:%M:%S"
PROBE_TZ = "America/New_York"


def _clear(ctx):
    ctx.execute("DELETE FROM consult_bookings WHERE note LIKE 'A40%' OR note IS NULL "
                "AND application_id IS NULL")
    ctx.execute("DELETE FROM consult_windows WHERE created_by = 'a40-probe'")
    ctx.execute("DELETE FROM consult_blackouts WHERE created_by = 'a40-probe'")


def _seed(ctx):
    """One window, on a weekday chosen so it always falls inside the horizon."""
    from monti import consults
    consults.add_window(weekday=2, start_local="09:00", end_local="12:00",
                        host_tz=PROBE_TZ, slot_minutes=30, created_by="a40-probe")


def run(ctx):
    from monti import consults

    findings = []
    with ctx.app.app_context():
        _clear(ctx)

        # ---- an empty calendar offers nothing -----------------------------
        if consults.windows():
            findings.append(Finding(
                "consult_windows",
                "the harness could not reach an empty state — another window is "
                "present and the no-invention property cannot be checked"))
        elif consults.slots():
            findings.append(Finding(
                "consults.slots",
                "offered times with no window entered — every one of them is "
                "invented, and a calendar cell is a promise"))

        _seed(ctx)
        now = datetime.now(timezone.utc)
        offered = consults.slots(now=now)
        if not offered:
            findings.append(Finding("consults.slots",
                                    "a window was entered and nothing was offered"))
            _clear(ctx)
            return findings

        tz = ZoneInfo(PROBE_TZ)
        # ---- provenance: walk every slot back to the window ---------------
        for stamp, minutes in offered:
            local = (datetime.strptime(stamp, FMT).replace(tzinfo=timezone.utc)
                     .astimezone(tz))
            if local.weekday() != 2:
                findings.append(Finding(
                    f"consults.slots → {stamp}",
                    f"lands on {local:%A} in {PROBE_TZ}, and the only window "
                    "entered is a Wednesday"))
            if not ("09:00" <= local.strftime("%H:%M") < "12:00"):
                findings.append(Finding(
                    f"consults.slots → {stamp}",
                    f"is {local:%H:%M} local, outside the 09:00-12:00 window "
                    "that is the only thing published"))
            if minutes != 30:
                findings.append(Finding(
                    f"consults.slots → {stamp}",
                    f"is {minutes} minutes; the window says 30"))

        # ---- daylight saving: the local time must never move --------------
        far = consults.slots(now=now, horizon_days=200)
        locals_seen = {
            (datetime.strptime(s, FMT).replace(tzinfo=timezone.utc)
             .astimezone(tz).strftime("%H:%M")) for s, _ in far}
        outside = sorted(t for t in locals_seen if not ("09:00" <= t < "12:00"))
        if outside:
            findings.append(Finding(
                "consults.slots (200-day horizon)",
                f"the window drifts across a daylight-saving change — local times "
                f"{outside} appear, and the window is 09:00-12:00. A slot stored "
                "against a fixed offset does exactly this, twice a year"))

        # ---- lead time -----------------------------------------------------
        soonest = datetime.strptime(offered[0][0], FMT).replace(tzinfo=timezone.utc)
        if soonest < now + timedelta(hours=consults.LEAD_HOURS) - timedelta(minutes=1):
            findings.append(Finding(
                f"consults.slots → {offered[0][0]}",
                f"is inside the {consults.LEAD_HOURS}h notice period — a call in "
                "minutes is not an offer, it is an ambush"))

        # ---- subtraction: booking removes it -------------------------------
        app_row = ctx.query("SELECT * FROM applications ORDER BY id LIMIT 1")
        if not app_row:
            app_id = ctx.execute(
                "INSERT INTO applications (ref, customer_id, company_name, contact_name, "
                "email) VALUES ('MMI-A-A40', ?, 'A40 Probe Co', 'A40', 'a40@example.test')",
                (ctx.member_customer_id,))
            app_row = ctx.query("SELECT * FROM applications WHERE id = ?", (app_id,))
        application = app_row[0]

        target = offered[0][0]
        booking = None
        try:
            booking = consults.book(application, target, guest_tz="Europe/London",
                                    note="A40 probe", now=now)
        except Exception as exc:                                  # noqa: BLE001
            findings.append(Finding("consults.book",
                                    f"refused a slot it had just offered: {exc}"))

        if booking is not None:
            if any(s == target for s, _ in consults.slots(now=now)):
                findings.append(Finding(
                    f"consults.slots → {target}",
                    "is still offered after being booked — the next applicant is "
                    "being sold a slot that is gone"))

            # ---- uniqueness, by actually trying it -------------------------
            try:
                consults.book(application, target, guest_tz="UTC",
                              note="A40 probe double", now=now)
                findings.append(Finding(
                    "consult_bookings.starts_at",
                    "the same slot was booked twice. Two people now hold one "
                    "call, and neither knows"))
            except consults.SlotGone:
                pass
            except Exception as exc:                              # noqa: BLE001
                findings.append(Finding("consults.book",
                                        f"raised {type(exc).__name__} instead of SlotGone"))

            if consults.booking_for(application["id"]) is None:
                findings.append(Finding("consults.booking_for",
                                        "cannot find the booking it just wrote"))
            # It has to reach the calendar the team looks at.
            if not ctx.query("SELECT id FROM calendar_events WHERE starts_at = ? "
                             "AND kind = 'CALL'", (target,)):
                findings.append(Finding(
                    "calendar_events",
                    "the consultation was booked and never reached the calendar — "
                    "a booking nobody sees is a missed call"))

        # ---- subtraction: a blackout removes the rest of that day ----------
        remaining = consults.slots(now=now)
        if remaining:
            day = remaining[0][0][:10]
            consults.add_blackout(f"{day} 00:00:00", f"{day} 23:59:59",
                                  "A40 probe", "a40-probe")
            still = [s for s, _ in consults.slots(now=now) if s.startswith(day)]
            if still:
                findings.append(Finding(
                    f"consults.slots → {day}",
                    f"{len(still)} slots survived a blackout covering the whole day"))

        # ---- the door: a real slot, posted the way the form posts it -------
        #
        # This check missed a live defect once. It called `book` directly with
        # the storage format, while the picker posts `2026-09-01T13:30:00Z` —
        # the same instant, a different string — so every genuine booking was
        # rejected and the applicant saw "that time is no longer available".
        # Every part of the calendar passed. Only the round trip failed, so only
        # a round trip catches it.
        remaining_now = consults.slots(now=now)
        if remaining_now:
            wire = remaining_now[0][0].replace(" ", "T") + "Z"
            if consults.canonical(wire) != remaining_now[0][0]:
                findings.append(Finding(
                    "consults.canonical",
                    f"cannot normalise {wire!r}, which is exactly what the picker posts"))
            token = ctx.csrf(ctx.public_client)
            ctx.public_client.post("/apply", data={
                "_csrf": token, "company_name": "A40 Round Trip",
                "contact_name": "A40", "email": "a40-round@example.test",
                "what_they_sell": "probe", "why": "probe",
                "consult_slot": wire, "consult_tz": "Europe/London",
                "consult_channel": "video"}, follow_redirects=True)
            if not ctx.query("SELECT id FROM consult_bookings WHERE starts_at = ?",
                             (remaining_now[0][0],)):
                findings.append(Finding(
                    "POST /apply",
                    f"posting {wire} booked nothing, and that slot was open. The "
                    "form and the store disagree about how a time is written, "
                    "and the applicant is told the slot is gone"))
            ctx.execute("DELETE FROM consult_bookings WHERE starts_at = ?",
                        (remaining_now[0][0],))
            ctx.execute("DELETE FROM calendar_events WHERE starts_at = ?",
                        (remaining_now[0][0],))
            ctx.execute("DELETE FROM applications WHERE company_name = 'A40 Round Trip'")
            ctx.execute("DELETE FROM crm_activities WHERE customer_id IN "
                        "(SELECT id FROM customers WHERE company_name = 'A40 Round Trip')")
            ctx.execute("DELETE FROM customers WHERE company_name = 'A40 Round Trip'")

        # ---- the door: a slot that was never offered must not book ---------
        invented = (now + timedelta(days=3)).replace(
            hour=3, minute=17, second=0, microsecond=0).strftime(FMT)
        if consults.is_open(invented):
            findings.append(Finding("consults.is_open",
                                    f"reports {invented} open; no window covers it"))
        token = ctx.csrf(ctx.public_client)
        before = ctx.query("SELECT COUNT(*) AS c FROM consult_bookings")[0]["c"]
        ctx.public_client.post("/apply", data={
            "_csrf": token, "company_name": "A40 Door Probe", "contact_name": "A40",
            "email": f"a40-door-{before}@example.test", "what_they_sell": "probe",
            "why": "probe", "consult_slot": invented, "consult_tz": "UTC"},
            follow_redirects=True)
        if ctx.query("SELECT id FROM consult_bookings WHERE starts_at = ?", (invented,)):
            findings.append(Finding(
                "POST /apply",
                "booked a time that was never offered — the posted value was "
                "trusted because the picker usually produces it"))
        ctx.execute("DELETE FROM applications WHERE company_name = 'A40 Door Probe'")
        ctx.execute("DELETE FROM customers WHERE company_name = 'A40 Door Probe'")

        _clear(ctx)
        ctx.execute("DELETE FROM calendar_events WHERE notes LIKE '%A40%' OR title LIKE '%A40%'")
        ctx.execute("DELETE FROM crm_activities WHERE body LIKE '%MMI-A-A40%'")
        ctx.execute("DELETE FROM applications WHERE ref = 'MMI-A-A40'")
    return findings


def prove(ctx):
    """Four defects, each one a real way booking calendars go wrong."""
    from pathlib import Path

    caught = []
    source = Path(__file__).resolve().parents[2] / "monti" / "consults.py"
    public = Path(__file__).resolve().parents[2] / "monti" / "blueprints" / "public.py"

    def attempt(label, path, before, after, matches):
        original = path.read_text()
        broken = original.replace(before, after, 1)
        assert broken != original, f"proof {label!r} no longer matches the source"
        path.write_text(broken)
        try:
            ctx.reload()
            hits = [f for f in run(ctx) if matches(f)]
            caught.append((label, bool(hits), str(hits[0]) if hits else "MISSED"))
        finally:
            path.write_text(original)
            ctx.reload()

    # 1. The nine-to-five grid: slots invented when nobody entered a window.
    attempt("the calendar invented a default working day", source,
            "    rows = windows()\n    if not rows:\n        return []",
            "    rows = windows()\n    if not rows:\n"
            "        rows = [{'weekday': d, 'start_local': '09:00', 'end_local': '17:00',\n"
            "                 'host_tz': 'UTC', 'slot_minutes': 30, 'effective_from': None,\n"
            "                 'effective_to': None} for d in range(5)]",
            lambda f: "invented" in f.detail)

    # 2. A booked slot stays on the calendar.
    attempt("a booked slot was still offered", source,
            "    taken = _taken()", "    taken = set()",
            lambda f: "still offered after being booked" in f.detail)

    # 3. Fixed offsets instead of a zone — the twice-a-year drift.
    attempt("the window was resolved against a fixed offset", source,
            "        try:\n            tz = ZoneInfo(w[\"host_tz\"])",
            "        try:\n            tz = timezone(ZoneInfo(w[\"host_tz\"]).utcoffset(now))",
            lambda f: "drifts across a daylight-saving change" in f.detail
            or "outside the 09:00-12:00 window" in f.detail)

    # 4. The door trusts the posted slot.
    #
    # The first version of this proof removed only the route's `is_open` check
    # and MISSED: `book` re-derives availability too, so the module refused what
    # the view let through. That is defence in depth working, and it also means
    # the check had not been shown to fail on this property — an unproven check
    # does not count (§0.2.7).
    #
    # So the proof now removes BOTH, which is the realistic defect: someone
    # "simplifies" by trusting the picker that produced the value, on the
    # reasoning that the page only ever offers real slots.
    def attempt_pair(label, matches):
        orig_pub, orig_src = public.read_text(), source.read_text()
        pub = orig_pub.replace(
            "    if slot and not consults.is_open(slot):\n"
            "        errors.append(\"That consultation time is no longer available. "
            "Please pick another.\")",
            "    if False:\n        pass", 1)
        src = orig_src.replace(
            "    minutes = slot_minutes_for(starts_at, now=now)\n"
            "    if minutes is None:\n"
            "        raise SlotGone(\"that time is no longer available\")",
            "    minutes = slot_minutes_for(starts_at, now=now) or 30", 1)
        assert pub != orig_pub and src != orig_src, "proof 4 no longer matches the source"
        public.write_text(pub); source.write_text(src)
        try:
            ctx.reload()
            hits = [f for f in run(ctx) if matches(f)]
            caught.append((label, bool(hits), str(hits[0]) if hits else "MISSED"))
        finally:
            public.write_text(orig_pub); source.write_text(orig_src)
            ctx.reload()

    attempt_pair("both guards dropped, so the posted slot was trusted",
                 lambda f: "never offered" in f.detail)

    # 5. The wire format and the storage format drift apart. This is the defect
    #    that actually shipped for an hour: every real booking was refused and
    #    the applicant was told the slot had gone.
    attempt("the posted time format stopped matching the stored one", source,
            '    text = stamp.strip().replace("T", " ")',
            '    text = stamp.strip()',
            lambda f: "booked nothing" in f.detail or "cannot normalise" in f.detail)

    missed = [name for name, ok, _ in caught if not ok]
    return (not missed), "; ".join(f"{n} -> {d}" for n, _, d in caught)


CHECKS = [Check("A40", "Every offered consultation slot traces to entered availability",
                run, prove)]
