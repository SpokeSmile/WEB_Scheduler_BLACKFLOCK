from datetime import date, datetime, timedelta

from django.db.models import Min
from django.utils import timezone

from .models import RosterState, ScheduleSlot

# Weekly roster helpers. Older weeks are retained as history, so advancing the
# active week must never delete ScheduleSlot rows.

MONTH_NAMES_GENITIVE = {
    1: 'Января',
    2: 'Февраля',
    3: 'Марта',
    4: 'Апреля',
    5: 'Мая',
    6: 'Июня',
    7: 'Июля',
    8: 'Августа',
    9: 'Сентября',
    10: 'Октября',
    11: 'Ноября',
    12: 'Декабря',
}


def week_start_for(day=None):
    current_day = day or timezone.localdate()
    if isinstance(current_day, datetime):
        current_day = current_day.date()
    return current_day - timedelta(days=current_day.weekday())


def parse_week_start(raw_value):
    if not raw_value:
        return None
    try:
        requested_day = date.fromisoformat(str(raw_value).strip())
    except ValueError as exc:
        raise ValueError('Invalid week date.') from exc
    return week_start_for(requested_day)


def week_range_label(week_start):
    week_end = week_start + timedelta(days=6)
    start_month = MONTH_NAMES_GENITIVE[week_start.month]
    end_month = MONTH_NAMES_GENITIVE[week_end.month]
    return f'{week_start.day} {start_month} - {week_end.day} {end_month}'


def ensure_current_roster_week(today=None, force=False):
    week_start = week_start_for(today)
    state, _created = RosterState.objects.get_or_create(
        pk=1,
        defaults={'current_week_start': week_start},
    )

    if state.current_week_start is None:
        state.current_week_start = week_start
        state.save(update_fields=['current_week_start', 'updated_at'])
        return False, 0

    if not force and state.current_week_start >= week_start:
        return False, 0

    state.current_week_start = week_start
    state.save(update_fields=['current_week_start', 'updated_at'])
    return True, 0


def get_current_week_start():
    ensure_current_roster_week()
    state = RosterState.objects.filter(pk=1).first()
    return state.current_week_start if state and state.current_week_start else week_start_for()


def get_earliest_filled_week_start(fallback_week_start=None):
    fallback_week_start = fallback_week_start or get_current_week_start()
    earliest_week = ScheduleSlot.objects.aggregate(value=Min('week_start'))['value']
    if earliest_week and earliest_week < fallback_week_start:
        return earliest_week
    return fallback_week_start


def is_week_editable(week_start, current_week_start=None):
    current_week_start = current_week_start or get_current_week_start()
    return week_start >= current_week_start
