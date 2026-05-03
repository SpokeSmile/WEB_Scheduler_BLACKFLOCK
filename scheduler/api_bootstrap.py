from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET

from .api_serializers import (
    build_days,
    build_timestamp_label,
    discord_payload,
    get_discord_connection_for_user,
    serialize_day_event,
    serialize_player,
    serialize_slot,
    serialize_staff_member,
)
from .models import DayEventType, Player, ScheduleSlot, StaffMember
from .profile_lookup import get_current_player, get_current_staff_member
from .roster import (
    ensure_current_roster_week,
    get_current_week_start,
    is_week_editable,
    parse_week_start,
    week_range_label,
)


@require_GET
@login_required
def bootstrap(request):
    ensure_current_roster_week()
    current_week_start = get_current_week_start()
    try:
        selected_week_start = parse_week_start(request.GET.get('week')) or current_week_start
    except ValueError:
        return JsonResponse({'error': 'Некорректная неделя.'}, status=400)

    can_edit_selected_week = is_week_editable(selected_week_start, current_week_start)
    current_player = get_current_player(request.user)
    current_staff_member = get_current_staff_member(request.user)
    current_connection = get_discord_connection_for_user(request.user)
    players = list(Player.objects.select_related('user__discord_connection'))
    staff_members = list(StaffMember.objects.select_related('user__discord_connection'))
    slots = ScheduleSlot.objects.select_related('player').filter(week_start=selected_week_start)
    day_events = list(DayEventType.objects.filter(week_start=selected_week_start))
    day_event_map = {day_event.day_of_week: day_event for day_event in day_events}
    user_discord = discord_payload(current_connection)

    return JsonResponse({
        'csrfToken': get_token(request),
        'user': {
            'username': request.user.username,
            'isStaff': request.user.is_staff,
            'playerId': current_player.id if current_player else None,
            'staffMemberId': current_staff_member.id if current_staff_member else None,
            'profileType': 'player' if current_player else ('staff' if current_staff_member else ''),
            **user_discord,
        },
        'selectedWeekStart': selected_week_start.isoformat(),
        'currentWeekStart': current_week_start.isoformat(),
        'weekRangeLabel': week_range_label(selected_week_start),
        'canEditSelectedWeek': can_edit_selected_week,
        'days': build_days(selected_week_start),
        'players': [serialize_player(player, current_player) for player in players],
        'staffMembers': [serialize_staff_member(staff_member, current_staff_member) for staff_member in staff_members],
        'slots': [serialize_slot(slot, current_player, day_event_map, can_edit_selected_week) for slot in slots],
        'dayEventTypes': [serialize_day_event(day_event) for day_event in day_events],
        'eventTypes': ScheduleSlot.event_types_payload(),
        'lastUpdated': build_timestamp_label(),
    })
