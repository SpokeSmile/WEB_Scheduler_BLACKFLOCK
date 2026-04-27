import json
from datetime import timedelta

from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import ScheduleSlotForm
from .models import Player, ScheduleSlot
from .views import get_current_player


def build_days():
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    return [
        {
            'value': value,
            'label': label,
            'date': (week_start + timedelta(days=value)).strftime('%d.%m'),
        }
        for value, label in ScheduleSlot.DAY_CHOICES
    ]


def avatar_url(player):
    if player.avatar:
        return player.avatar.url
    return ''


def serialize_player(player, current_player):
    return {
        'id': player.id,
        'name': player.name,
        'role': player.role,
        'initial': player.initial,
        'avatarUrl': avatar_url(player),
        'canEdit': current_player == player,
    }


def serialize_slot(slot, current_player):
    return {
        'id': slot.id,
        'playerId': slot.player_id,
        'slotType': slot.slot_type,
        'eventType': slot.event_type,
        'eventLabel': slot.event_label,
        'eventDescription': slot.event_description,
        'eventTone': slot.event_tone,
        'dayOfWeek': slot.day_of_week,
        'startTimeMinutes': slot.start_time_minutes,
        'endTimeMinutes': slot.end_time_minutes,
        'startLabel': slot.start_label,
        'endLabel': slot.end_label,
        'timeRange': slot.time_range if slot.is_available else '',
        'label': slot.label,
        'note': slot.note,
        'displayNote': slot.display_note,
        'canEdit': current_player == slot.player,
    }


def parse_body(request):
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return None


def form_data_from_payload(payload):
    return {
        'slot_type': payload.get('slotType') or ScheduleSlot.AVAILABLE,
        'event_type': payload.get('eventType') or '',
        'day_of_week': payload.get('dayOfWeek'),
        'start_time_minutes': payload.get('startTimeMinutes'),
        'end_time_minutes': payload.get('endTimeMinutes'),
        'note': payload.get('note') or '',
    }


def form_errors_payload(form):
    return {
        field: [error['message'] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


@require_GET
@login_required
def bootstrap(request):
    current_player = get_current_player(request.user)
    players = list(Player.objects.prefetch_related('slots'))
    slots = ScheduleSlot.objects.select_related('player').all()

    return JsonResponse({
        'csrfToken': get_token(request),
        'user': {
            'username': request.user.username,
            'isStaff': request.user.is_staff,
            'playerId': current_player.id if current_player else None,
            'avatarUrl': avatar_url(current_player) if current_player else '',
        },
        'days': build_days(),
        'players': [serialize_player(player, current_player) for player in players],
        'slots': [serialize_slot(slot, current_player) for slot in slots],
        'eventTypes': ScheduleSlot.event_types_payload(),
        'lastUpdated': timezone.localtime().strftime('%d.%m.%Y %H:%M'),
    })


@require_POST
@login_required
def slot_create(request):
    current_player = get_current_player(request.user)
    if current_player is None:
        return JsonResponse({'error': 'Аккаунт не привязан к игроку.'}, status=403)

    payload = parse_body(request)
    if payload is None:
        return JsonResponse({'error': 'Некорректный JSON.'}, status=400)

    form = ScheduleSlotForm(form_data_from_payload(payload))
    if not form.is_valid():
        return JsonResponse({'errors': form_errors_payload(form)}, status=400)

    slot = form.save(commit=False)
    slot.player = current_player
    slot.full_clean()
    slot.save()

    return JsonResponse({'slot': serialize_slot(slot, current_player)}, status=201)


@require_http_methods(['PATCH', 'POST'])
@login_required
def slot_update(request, pk):
    current_player = get_current_player(request.user)
    if current_player is None:
        return JsonResponse({'error': 'Аккаунт не привязан к игроку.'}, status=403)

    slot = get_object_or_404(ScheduleSlot, pk=pk, player=current_player)
    payload = parse_body(request)
    if payload is None:
        return JsonResponse({'error': 'Некорректный JSON.'}, status=400)

    form = ScheduleSlotForm(form_data_from_payload(payload), instance=slot)
    if not form.is_valid():
        return JsonResponse({'errors': form_errors_payload(form)}, status=400)

    slot = form.save(commit=False)
    slot.player = current_player
    slot.full_clean()
    slot.save()

    return JsonResponse({'slot': serialize_slot(slot, current_player)})


@require_http_methods(['DELETE', 'POST'])
@login_required
def slot_delete(request, pk):
    current_player = get_current_player(request.user)
    if current_player is None:
        return JsonResponse({'error': 'Аккаунт не привязан к игроку.'}, status=403)

    slot = get_object_or_404(ScheduleSlot, pk=pk, player=current_player)
    slot.delete()

    return JsonResponse({'deleted': True})


@require_POST
@login_required
def logout_view(request):
    logout(request)
    return JsonResponse({'ok': True, 'redirectUrl': '/login/'})
