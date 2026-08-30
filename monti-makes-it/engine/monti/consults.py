"""Booking a consultation: the slots, and the rule that none of them are invented.

CHG-021 asked for a calendar on the application form that sets a date and time.
The easy version of this is a grid of half-hours from nine to five. It is also
the version that lies: it offers times nobody agreed to be available for, and
the applicant discovers that when they join a call alone.

So there is no constant in here that becomes a slot. Every offered time is
derived, in this order:

    windows       a recurring weekly window an admin entered, in the host's own
                  timezone — Tuesday 09:00-12:00 America/New_York, 30 minutes
    minus         any blackout range covering it
    minus         any slot already booked
    minus         anything inside the lead time, because a call in twenty
                  minutes is not a slot, it is an ambush

If nobody has entered a window, there are no slots and the page says so. That
is the correct empty state, and it is why `flask launch` seeds none: the hours
Monti is willing to take calls are Monti's to enter, not this module's to guess.

TIMEZONES

Windows are stored as local wall-clock time plus an IANA zone, never as a UTC
offset. An offset is wrong for half the year: "14:00 UTC-5" silently becomes the
wrong hour the day the clocks change, and the applicant is the one who finds
out. Resolving the zone at generation time means a window entered as "Tuesday
9am New York" is 9am in New York in January and 9am in New York in July.

Everything crossing the boundary into storage is UTC. The guest's own zone is
stored on the booking, because the time to show a person is the time on their
own clock and reconstructing that later from a location field is guesswork.

DOUBLE BOOKING

`consult_bookings.starts_at` is UNIQUE. Two people clicking the same slot at the
same moment cannot both succeed: the second INSERT raises, and `book` turns that
into a refusal the caller can render. A check that reads then writes would let
both through, and the gap is exactly as long as it takes to render a page.
"""
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .db import execute, query

# A call booked for twenty minutes' time is not a booking anyone can keep.
LEAD_HOURS = 24
# How far out the calendar offers. Beyond this, availability entered today is a
# guess about a month that has not happened yet.
HORIZON_DAYS = 45

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
CHANNELS = [("video", "Video call"), ("phone", "Phone call")]

# Offered in the picker, most-used first. The browser's detected zone is added
# to this list when it is not already in it, so nobody is forced to pick a city
# they do not live in.
COMMON_ZONES = [
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Toronto", "America/Mexico_City", "America/Sao_Paulo",
    "Europe/London", "Europe/Dublin", "Europe/Lisbon", "Europe/Madrid", "Europe/Paris",
    "Europe/Berlin", "Europe/Rome", "Europe/Amsterdam", "Europe/Stockholm",
    "Europe/Warsaw", "Europe/Athens", "Europe/Istanbul", "Europe/Moscow",
    "Africa/Lagos", "Africa/Johannesburg", "Africa/Cairo", "Africa/Nairobi",
    "Asia/Dubai", "Asia/Karachi", "Asia/Kolkata", "Asia/Dhaka", "Asia/Bangkok",
    "Asia/Jakarta", "Asia/Shanghai", "Asia/Hong_Kong", "Asia/Singapore",
    "Asia/Seoul", "Asia/Tokyo", "Australia/Perth", "Australia/Sydney",
    "Pacific/Auckland", "UTC",
]

FMT = "%Y-%m-%d %H:%M:%S"


def valid_zone(name):
    """The zone if it exists, otherwise None. Never raises on user input."""
    if not name:
        return None
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return None
    return name


def canonical(stamp):
    """The storage form of a slot the browser sent back, or None if it is junk.

    The picker receives slots as `2026-09-01T13:30:00Z` because that is what
    `new Date()` parses reliably in every browser, and it posts back what it was
    given. Storage uses `2026-09-01 13:30:00`. Those are the same instant and
    not the same string, so comparing the posted value directly against the
    generated set rejected every real booking while looking exactly like a
    "slot no longer available" race.

    Normalising here, in one place, is the fix. Doing it in the view would leave
    the next caller to rediscover the same mismatch.
    """
    if not stamp:
        return None
    text = stamp.strip().replace("T", " ")
    if text.endswith("Z"):
        text = text[:-1]
    text = text.strip()
    if len(text) == 16:                       # no seconds: '2026-09-01 13:30'
        text += ":00"
    try:
        datetime.strptime(text, FMT)
    except ValueError:
        return None
    return text


def _utc(dt):
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _parse(text):
    return datetime.strptime(text, FMT).replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# What an admin entered
# ---------------------------------------------------------------------------
def windows(include_inactive=False):
    sql = "SELECT * FROM consult_windows"
    if not include_inactive:
        sql += " WHERE active = 1"
    return query(sql + " ORDER BY weekday, start_local")


def add_window(weekday, start_local, end_local, host_tz, slot_minutes=30,
               effective_from=None, effective_to=None, created_by=None):
    if valid_zone(host_tz) is None:
        raise ValueError(f"unknown timezone: {host_tz!r}")
    if not (0 <= int(weekday) <= 6):
        raise ValueError("weekday must be 0 (Monday) to 6 (Sunday)")
    if int(slot_minutes) < 5:
        raise ValueError("a slot shorter than five minutes is not a meeting")
    if start_local >= end_local:
        raise ValueError("the window ends before it starts")
    # Two identical windows generate the same slots, and `slots()` de-duplicates,
    # so this is not a correctness bug — it is a list of six rows describing
    # three, which is its own kind of wrong on a page someone has to read.
    if query("SELECT id FROM consult_windows WHERE active = 1 AND weekday = ? "
             "AND start_local = ? AND end_local = ? AND host_tz = ? AND slot_minutes = ?",
             (int(weekday), start_local, end_local, host_tz, int(slot_minutes)), one=True):
        raise ValueError("that window is already published")
    return execute(
        "INSERT INTO consult_windows (weekday, start_local, end_local, host_tz, "
        "slot_minutes, effective_from, effective_to, created_by) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (int(weekday), start_local, end_local, host_tz, int(slot_minutes),
         effective_from or None, effective_to or None, created_by))


def deactivate_window(window_id):
    execute("UPDATE consult_windows SET active = 0 WHERE id = ?", (window_id,))


def blackouts():
    return query("SELECT * FROM consult_blackouts ORDER BY starts_at")


def add_blackout(starts_at, ends_at, reason=None, created_by=None):
    return execute(
        "INSERT INTO consult_blackouts (starts_at, ends_at, reason, created_by) "
        "VALUES (?, ?, ?, ?)", (starts_at, ends_at, reason, created_by))


def remove_blackout(blackout_id):
    execute("DELETE FROM consult_blackouts WHERE id = ?", (blackout_id,))


# ---------------------------------------------------------------------------
# Generating the offer
# ---------------------------------------------------------------------------
def _taken():
    return {r["starts_at"] for r in query(
        "SELECT starts_at FROM consult_bookings WHERE status = 'BOOKED'")}


def _blackout_ranges():
    return [(_parse(r["starts_at"]), _parse(r["ends_at"])) for r in blackouts()]


def slots(now=None, horizon_days=HORIZON_DAYS, lead_hours=LEAD_HOURS):
    """Every bookable slot, as UTC datetimes, soonest first.

    Generated by walking each window's own timezone day by day. Walking the
    HOST's local days rather than UTC days is what makes a 09:00 window stay at
    09:00 across a daylight-saving change; iterating UTC and adding a fixed
    offset is the version that drifts by an hour twice a year.
    """
    now = now or datetime.now(timezone.utc)
    rows = windows()
    if not rows:
        return []

    taken = _taken()
    blacked = _blackout_ranges()
    earliest = now + timedelta(hours=lead_hours)
    latest = now + timedelta(days=horizon_days)

    found = set()
    for w in rows:
        try:
            tz = ZoneInfo(w["host_tz"])
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            # A window whose zone no longer resolves is a defect to surface, not
            # a reason to fall back to a guess. `broken_windows` reports it.
            continue
        step = timedelta(minutes=w["slot_minutes"])
        s_h, s_m = (int(x) for x in w["start_local"].split(":"))
        e_h, e_m = (int(x) for x in w["end_local"].split(":"))

        # Start a day early and end a day late: a window near midnight in a zone
        # far from UTC can fall inside the range on a local day just outside it.
        day = (now.astimezone(tz) - timedelta(days=1)).date()
        end_day = (latest.astimezone(tz) + timedelta(days=1)).date()
        while day <= end_day:
            if day.weekday() == w["weekday"] and _in_effect(w, day):
                start = datetime.combine(day, datetime.min.time(), tz).replace(
                    hour=s_h, minute=s_m)
                stop = datetime.combine(day, datetime.min.time(), tz).replace(
                    hour=e_h, minute=e_m)
                cursor = start
                while cursor + step <= stop:
                    utc = cursor.astimezone(timezone.utc)
                    if earliest <= utc <= latest:
                        key = _utc(cursor).strftime(FMT)
                        if key not in taken and not _blacked(utc, utc + step, blacked):
                            found.add((key, w["slot_minutes"]))
                    cursor += step
            day += timedelta(days=1)
    return sorted(found)


def _in_effect(window, day):
    iso = day.isoformat()
    if window["effective_from"] and iso < window["effective_from"]:
        return False
    if window["effective_to"] and iso > window["effective_to"]:
        return False
    return True


def _blacked(start, end, ranges):
    return any(start < b_end and end > b_start for b_start, b_end in ranges)


def broken_windows():
    """Windows whose timezone no longer resolves, so they generate nothing.

    Silent in every other way: the calendar simply has fewer days on it, which
    looks like a quiet week. Surfaced on the admin page instead.
    """
    return [w for w in windows() if valid_zone(w["host_tz"]) is None]


def is_open(starts_at, now=None):
    """Whether this exact UTC slot is one the calendar is currently offering.

    The form's chosen slot is checked against this on submit rather than
    trusted. A posted value is not a click: it can be edited, replayed after the
    slot was taken, or sent by something that never rendered the page.
    """
    key = canonical(starts_at)
    return key is not None and any(s == key for s, _ in slots(now=now))


def slot_minutes_for(starts_at, now=None):
    key = canonical(starts_at)
    if key is None:
        return None
    for s, minutes in slots(now=now):
        if s == key:
            return minutes
    return None


# ---------------------------------------------------------------------------
# Booking
# ---------------------------------------------------------------------------
class SlotGone(Exception):
    """The slot was not open, or someone took it first."""


def book(application, starts_at, guest_tz, channel="video", phone=None, note=None,
         now=None):
    """Take a slot. Raises SlotGone rather than booking something unavailable.

    Both failure modes are the same message to the applicant and different
    causes: the slot was never open (a replayed or edited form), or it was open
    when the page rendered and gone by the time they clicked. The UNIQUE index
    is what catches the second one.
    """
    minutes = slot_minutes_for(starts_at, now=now)
    if minutes is None:
        raise SlotGone("that time is no longer available")
    starts_at = canonical(starts_at)
    tz = valid_zone(guest_tz) or "UTC"
    if channel not in {c for c, _ in CHANNELS}:
        channel = "video"
    if channel == "phone" and not (phone or "").strip():
        raise ValueError("a phone call needs a number to call")
    ends = (_parse(starts_at) + timedelta(minutes=minutes)).strftime(FMT)
    try:
        booking_id = execute(
            "INSERT INTO consult_bookings (application_id, customer_id, starts_at, "
            "ends_at, guest_tz, channel, phone, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (application["id"], application["customer_id"], starts_at, ends, tz,
             channel, (phone or "").strip() or None, (note or "").strip() or None))
    except sqlite3.IntegrityError as exc:
        raise SlotGone("someone booked that time while you were filling this in") from exc

    execute("UPDATE applications SET status = 'INTERVIEW_SCHEDULED', interview_at = ?, "
            "updated_at = datetime('now') WHERE id = ?", (starts_at, application["id"]))
    # It belongs on the calendar the team actually looks at, not only on the
    # application. A booking nobody sees is a missed call.
    execute(
        "INSERT INTO calendar_events (title, customer_id, kind, starts_at, ends_at, "
        "location, notes, created_by) VALUES (?, ?, 'CALL', ?, ?, ?, ?, 'website')",
        (f"Consultation · {application['company_name']}", application["customer_id"],
         starts_at, ends, "Video call" if channel == "video" else f"Phone {phone or ''}".strip(),
         f"Booked from the application form ({application['ref']}). "
         f"Their timezone: {tz}." + (f" Note: {note}" if note else "")))
    execute("INSERT INTO crm_activities (customer_id, kind, body, author) "
            "VALUES (?, 'SYSTEM', ?, 'website')",
            (application["customer_id"],
             f"Booked a consultation for {starts_at} UTC ({tz}) against {application['ref']}"))
    return query("SELECT * FROM consult_bookings WHERE id = ?", (booking_id,), one=True)


def booking_for(application_id):
    return query("SELECT * FROM consult_bookings WHERE application_id = ? "
                 "AND status = 'BOOKED' ORDER BY id DESC", (application_id,), one=True)


def cancel(booking_id, by=None):
    """Release a slot. The row stays: a cancelled call is part of the history.

    Deleting it would free the slot too — UNIQUE only constrains rows that
    exist — which is why the index is on `starts_at` alone and `_taken` filters
    on status rather than the index doing both jobs.
    """
    execute("UPDATE consult_bookings SET status = 'CANCELLED', cancelled_at = datetime('now'), "
            "cancelled_by = ? WHERE id = ?", (by, booking_id))


def upcoming(limit=25):
    return query(
        "SELECT b.*, a.ref AS application_ref, a.company_name, a.contact_name, a.email "
        "FROM consult_bookings b LEFT JOIN applications a ON a.id = b.application_id "
        "WHERE b.status = 'BOOKED' AND b.starts_at >= datetime('now') "
        "ORDER BY b.starts_at LIMIT ?", (limit,))
