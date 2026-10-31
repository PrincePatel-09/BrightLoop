import calendar
from datetime import date, timedelta


def add_billing_interval(start: date, interval: str, count: int) -> date:
    if interval == "day":
        return start + timedelta(days=count)
    if interval == "week":
        return start + timedelta(weeks=count)
    months = count if interval == "month" else count * 12
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))
