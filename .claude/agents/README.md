# The agents, and when they run

Everything measured has to run where egress works — GitHub Actions — because
the local sandbox blocks outbound traffic and answers CONNECT with a 403 that
reads exactly like a site refusing us.

| When (Pacific) | What | Who |
|---|---|---|
| 6:00am daily | `watch.yml` measures every watched site | Actions |
| 6:30am weekdays | Reads the watch results, briefs Tyler | Routine |
| 7:30am Mon & Wed | Finds and vets new leads | `prospector` |
| 5:00pm Sunday | Reviews how the pages look, improves the builder | `designer` |

Nothing fires on top of anything else, and nothing fires while he is calling.

## Invoking them by hand

```
Use the prospector agent to find me new leads
Use the designer agent to fix the service menu spacing
```

## Changing the schedule

The routines live in the account, not this repo — `/routines` on claude.ai, or
ask in a session. The two Actions crons are in `.github/workflows/`.
