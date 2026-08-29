# Reproducing every number in this pack

QA-01 failed Phase 1 twice. The second failure named this: most figures here shipped
without a probe, so a reader could not check them, and its own extraction of the string
counts differed from mine under a different method. A number in an evidence pack that
cannot be re-derived is a claim, not evidence (§1.1).

Every probe now ships. Run from `monti-makes-it/engine`:

```
export PYTHONPATH=$PWD SECRET_KEY=x

# a launched database — one real client, no fixtures
export DATABASE_PATH=/tmp/p1.db && rm -f $DATABASE_PATH
FLASK_APP=monti .venv/bin/flask launch

.venv/bin/python <this dir>/surfaces-generator.py        > surfaces.tsv
.venv/bin/python <this dir>/chart-census-probe.py        > chart-census.txt
.venv/bin/python <this dir>/document-baseline-probe.py   > document-baseline.txt
.venv/bin/python <this dir>/render-census-probe.py       > render-census.txt
.venv/bin/python <this dir>/string-census-probe.py       > string-census.txt
.venv/bin/python <this dir>/fixture-probe.py             > fixture-probe.txt
.venv/bin/python <this dir>/impersonation-probe.py       > impersonation-baseline.txt
```

The two browser probes need the app served and Chromium:

```
DATABASE_PATH=/tmp/p1.db .venv/bin/python -c \
  "from monti import create_app; create_app().run(port=5058)" &
node <this dir>/computed-style-probe.mjs      # CHG-001 on a launched db
```

`meter-probe.mjs` needs rows to draw, so it runs against a **throwaway seeded**
database on port 5059:

```
export DATABASE_PATH=/tmp/seeded.db && rm -f $DATABASE_PATH
FLASK_APP=monti .venv/bin/flask seed
DATABASE_PATH=/tmp/seeded.db .venv/bin/python -c \
  "from monti import create_app; create_app().run(port=5059)" &
node <this dir>/meter-probe.mjs
```

That seed is the case §1.5 explicitly permits — *"an explicitly labelled local
development seed"*. It is a throwaway file, never served to a client, and exists only so
the share bars have rows to fail to draw. Nothing from it reaches a client-facing
surface, and the launched database used for every other probe contains zero fixture rows.

## Known method sensitivities

The string counts move with the pattern, so the pattern is stated rather than the number
being presented as absolute:

- **template text nodes** — `>\s*([A-Z][^<>{}\n]{3,}?)\s*<`, i.e. a run starting with a
  capital, at least 4 characters, between tags, containing no Jinja braces. A looser
  pattern that counts lowercase fragments and interpolated runs gives a substantially
  higher figure. Neither is wrong; they answer different questions. This one approximates
  "sentences a translator would have to handle".
- **`/ 100`** — the literal two-token string. `/ 100000` contains it, so a naive count
  reads 32 where the money-conversion idiom appears 30 times.
- **hex literals** — `#[0-9a-fA-F]{3,8}\b` over templates only. `app.css` carries a
  further 82, which is where a token file's colours are supposed to live.
