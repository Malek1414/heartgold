import datetime
from src.cron import next_run


def test_daily():
    assert next_run("30 2 * * *", datetime.datetime(2026, 3, 1, 5, 0)) == datetime.datetime(2026, 3, 2, 2, 30)
