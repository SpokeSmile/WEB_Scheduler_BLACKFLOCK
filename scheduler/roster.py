from datetime import timedelta

from django.utils import timezone

from .models import RosterState, ScheduleSlot

# Weekly roster reset helpers. The reset intentionally deletes only ScheduleSlot
# rows; players, staff, profile data, Discord links, BattleTags and cached
# statistics must survive week changes.


def week_start_for(day=None):
    current_day = day or timezone.localdate()
    return current_day - timedelta(days=current_day.weekday())


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

    # The schedule is current-week only by product decision; historical slots are
    # not retained until a separate snapshots/statistics model is introduced.
    deleted_count, _detail = ScheduleSlot.objects.all().delete()
    state.current_week_start = week_start
    state.last_reset_at = timezone.now()
    state.save(update_fields=['current_week_start', 'last_reset_at', 'updated_at'])
    return True, deleted_count
