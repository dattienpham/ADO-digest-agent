from datetime import datetime
import pytz
import holidays
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")


def is_working_day(dt: datetime) -> bool:
    local = dt.astimezone(VN_TZ)
    if local.weekday() >= 5:
        return False
    vn_holidays = holidays.Vietnam(years=local.year)
    if local.date() in vn_holidays:
        return False
    return True


def run_digest(run_time: datetime = None):
    if run_time is None:
        run_time = datetime.now(pytz.utc)

    if not is_working_day(run_time):
        print(f"[scheduler] Skip — not a working day: {run_time.astimezone(VN_TZ).strftime('%Y-%m-%d %A')}")
        return

    print(f"[scheduler] Starting digest run: {run_time.astimezone(VN_TZ).strftime('%Y-%m-%d %H:%M')} UTC+7")

    from agent.orchestrator import orchestrate
    orchestrate(run_time)


def start_scheduler():
    scheduler = BlockingScheduler(timezone=VN_TZ)

    scheduler.add_job(run_digest, CronTrigger(hour=9, minute=0, day_of_week="mon-fri", timezone=VN_TZ))
    scheduler.add_job(run_digest, CronTrigger(hour=13, minute=0, day_of_week="mon-fri", timezone=VN_TZ))

    print("[scheduler] Jobs registered: 9:00 AM and 1:00 PM UTC+7, Mon-Fri")
    print("[scheduler] Waiting for next scheduled run...")
    scheduler.start()
