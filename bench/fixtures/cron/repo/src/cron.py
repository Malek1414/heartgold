"""Scheduler: when does a cron job run next?"""
import datetime


def next_run(expr, after):
    """Return the first datetime strictly after `after` matching the 5-field cron `expr`."""
    minute, hour, dom, month, dow = expr.split()
    t = after.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    for _ in range(60 * 24 * 366):
        if ((minute == "*" or t.minute == int(minute)) and (hour == "*" or t.hour == int(hour))
                and (dom == "*" or t.day == int(dom)) and (month == "*" or t.month == int(month))
                and (dow == "*" or t.isoweekday() % 7 == int(dow))):
            return t
        t += datetime.timedelta(minutes=1)
    raise ValueError("no match within a year")
