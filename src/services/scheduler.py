from datetime import datetime, timedelta


def next_run_time(hour: int = 8) -> datetime:
    now = datetime.now()
    run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=1)
    return run
