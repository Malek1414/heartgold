`next_run(expr, after)` must behave exactly like standard (Vixie) cron for the
5-field syntax used in crontab(5): lists, ranges, steps on ranges and on `*`,
month and day-of-week names (case-insensitive), both 0 and 7 meaning Sunday, and
the crontab rule for how day-of-month and day-of-week combine. Return the first
matching minute strictly after `after` (naive datetimes, seconds zero). It must
also be fast for sparse schedules (e.g. Feb 29 only). Standard library only (no
croniter).
