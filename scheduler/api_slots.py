from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST

from .api_serializers import serialize_slot
from .api_utils import form_errors_payload, parse_body
from .forms import ScheduleSlotForm
from .models import DayEventType, ScheduleSlot
from .profile_lookup import get_current_player
from .roster import ensure_current_roster_week


def form_data_from_payload(payload):
    return {
        'slot_type': payload.get('slotType') or ScheduleSlot.AVAILABLE,
        'day_of_week': payload.get('dayOfWeek'),
        'start_time_minutes': payload.get('startTimeMinutes'),
        'end_time_minutes': payload.get('endTimeMinutes'),
        'note': payload.get('note') or '',
    }


@require_POST
@login_required
def slot_create(request):
    ensure_current_roster_week()
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
    day_event_map = {slot.day_of_week: DayEventType.objects.filter(day_of_week=slot.day_of_week).first()}

    return JsonResponse({'slot': serialize_slot(slot, current_player, day_event_map)}, status=201)


@require_http_methods(['PATCH', 'POST'])
@login_required
def slot_update(request, pk):
    ensure_current_roster_week()
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
    day_event_map = {slot.day_of_week: DayEventType.objects.filter(day_of_week=slot.day_of_week).first()}

    return JsonResponse({'slot': serialize_slot(slot, current_player, day_event_map)})


@require_http_methods(['DELETE', 'POST'])
@login_required
def slot_delete(request, pk):
    ensure_current_roster_week()
    current_player = get_current_player(request.user)
    if current_player is None:
        return JsonResponse({'error': 'Аккаунт не привязан к игроку.'}, status=403)

    slot = get_object_or_404(ScheduleSlot, pk=pk, player=current_player)
    slot.delete()

    return JsonResponse({'deleted': True})
