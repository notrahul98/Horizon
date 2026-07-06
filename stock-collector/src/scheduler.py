"""
APScheduler-based job scheduler.

Jobs:
  - intraday     : every N minutes (configurable), fetches today's 5-min bars
  - daily        : each weekday at 18:00 (after US market close), fetches daily OHLCV
  - fundamentals : every Sunday at 08:00, fetches valuation metrics
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.collector import collect_historical, collect_intraday, collect_fundamentals

logger = logging.getLogger(__name__)


def build_scheduler(db_path: str, watchlist: list, schedules: dict,
                    historical_period: str, intraday_period: str,
                    intraday_interval: str) -> BlockingScheduler:

    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    scheduler.add_job(
        func=collect_intraday,
        trigger=IntervalTrigger(minutes=schedules["intraday_minutes"]),
        id="intraday",
        name="Intraday price collection",
        kwargs={
            "db_path": db_path,
            "watchlist": watchlist,
            "period": intraday_period,
            "interval": intraday_interval,
        },
        max_instances=1,
        misfire_grace_time=60,
    )

    scheduler.add_job(
        func=collect_historical,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour=schedules["daily_hour"],
            minute=schedules["daily_minute"],
        ),
        id="daily",
        name="Daily OHLCV sync",
        kwargs={
            "db_path": db_path,
            "watchlist": watchlist,
            "period": historical_period,
        },
        max_instances=1,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        func=collect_fundamentals,
        trigger=CronTrigger(
            day_of_week=schedules["weekly_day"],
            hour=schedules["weekly_hour"],
            minute=schedules["weekly_minute"],
        ),
        id="fundamentals",
        name="Weekly fundamentals snapshot",
        kwargs={"db_path": db_path, "watchlist": watchlist},
        max_instances=1,
        misfire_grace_time=3600,
    )

    return scheduler
