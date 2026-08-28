# Purge evidence

`flask purge-fixtures`, run against a freshly seeded database. Reproduce with:

```
flask --app app seed && flask --app app purge-fixtures
```

## Backup, taken before any deletion

- path: `/tmp/tmpfzxjqzk9/backups/purge-pre-purge-20260828T224456Z.db`
- customers in the backup: 10
- `PRAGMA integrity_check`: ok

The backup is reopened and counted before the delete is allowed to proceed —
a copy nobody has read back is a file, not a backup.

## Rows deleted, by table

| table | rows |
|---|---|
| applications | 5 |
| quotes | 21 |
| orders | 466 |
| catalog_items | 7 |
| ledger_entries | 0 |
| decision_items | 0 |
| customers | 10 |

Total fixture rows inventoried before deletion: **509**

## Orphan sweep

Zero orphans across the 19 dependent relationships checked in
`monti/purge.py:ORPHAN_CHECKS`. The sweep looks for them explicitly
rather than trusting `PRAGMA foreign_keys`, which is per-connection
and off by default — so a row written by a connection that forgot it
survives a cascade that appears to have worked.

## Remaining fixture rows

| table | remaining |
|---|---|
| customers | 0 |
| applications | 0 |
| quotes | 0 |
| orders | 0 |
| catalog_items | 0 |
| ledger_entries | 0 |
| decision_items | 0 |

Asserted continuously by `A14`, which also checks the named accounts from
§0.3.5 by name and sweeps for orphans on every run.
