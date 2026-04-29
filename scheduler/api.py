import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import ScheduleSlotForm
from .models import DayEventType, DiscordConnection, Player, ScheduleSlot, StaffMember
from .roster import ensure_current_roster_week
from .views import get_current_player, get_current_staff_member

DISCORD_AUTHORIZE_URL = 'https://discord.com/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
DISCORD_USER_URL = 'https://discord.com/api/users/@me'
DISCORD_STATE_SESSION_KEY = 'discord_oauth_state'


def resolve_build_timestamp():
    raw_value = os.environ.get('BUILD_TIMESTAMP')
    if raw_value:
        parsed = datetime.fromisoformat(raw_value.replace('Z', '+00:00'))
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed)
        return parsed
    return timezone.now()


BUILD_TIMESTAMP = resolve_build_timestamp()


def get_discord_connection_for_user(user):
    if not user or not getattr(user, 'pk', None):
        return None
    try:
        return user.discord_connection
    except DiscordConnection.DoesNotExist:
        return None


def discord_payload(connection):
    if connection is None:
        return {
            'discordConnected': False,
            'discordUsername': '',
            'discordGlobalName': '',
            'discordDisplayTag': '',
            'avatarUrl': '',
        }
    return {
        'discordConnected': True,
        'discordUsername': connection.username,
        'discordGlobalName': connection.global_name,
        'discordDisplayTag': connection.display_tag,
        'avatarUrl': connection.avatar_url,
    }


def build_profile_redirect(status=None, reason=None):
    params = {}
    if status:
        params['discord'] = status
    if reason:
        params['reason'] = reason
    target = reverse('profile')
    if params:
        return f'{target}?{urlencode(params)}'
    return target


def discord_oauth_configured():
    return all([
        settings.DISCORD_CLIENT_ID,
        settings.DISCORD_CLIENT_SECRET,
        settings.DISCORD_REDIRECT_URI,
    ])


def can_manage_profile(user):
    return get_current_player(user) is not None or get_current_staff_member(user) is not None


def exchange_code_for_token(code):
    response = requests.post(
        DISCORD_TOKEN_URL,
        data={
            'client_id': settings.DISCORD_CLIENT_ID,
            'client_secret': settings.DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.DISCORD_REDIRECT_URI,
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get('access_token', '')


def fetch_discord_identity(access_token):
    response = requests.get(
        DISCORD_USER_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


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


def serialize_player(player, current_player):
    payload = discord_payload(player.discord_connection)
    return {
        'id': player.id,
        'name': player.name,
        'role': player.role,
        'roleColor': player.role_color,
        'initial': player.initial,
        'avatarUrl': payload['avatarUrl'],
        'battleTags': player.battle_tags_list,
        'battleTagsText': '\n'.join(player.battle_tags_list),
        'discordConnected': payload['discordConnected'],
        'discordUsername': payload['discordUsername'],
        'discordGlobalName': payload['discordGlobalName'],
        'discordDisplayTag': payload['discordDisplayTag'],
        'canEdit': current_player == player,
    }


def serialize_staff_member(staff_member, current_staff_member=None):
    payload = discord_payload(staff_member.discord_connection)
    return {
        'id': staff_member.id,
        'name': staff_member.name,
        'role': staff_member.role,
        'roleColor': staff_member.role_color,
        'initial': staff_member.initial,
        'avatarUrl': payload['avatarUrl'],
        'discordConnected': payload['discordConnected'],
        'discordUsername': payload['discordUsername'],
        'discordGlobalName': payload['discordGlobalName'],
        'discordDisplayTag': payload['discordDisplayTag'],
        'canEdit': current_staff_member == staff_member,
    }


def serialize_day_event(day_event):
    return {
        'dayOfWeek': day_event.day_of_week,
        'eventType': day_event.event_type,
        'eventLabel': day_event.event_label,
        'eventDescription': day_event.event_description,
        'eventTone': day_event.event_tone,
    }


def event_meta_for_day(day_of_week, day_event_map):
    day_event = day_event_map.get(day_of_week)
    if not day_event or not day_event.event_type:
        return {
            'eventType': '',
            'eventLabel': 'Availability',
            'eventDescription': '',
            'eventTone': 'fallback',
        }

    return {
        'eventType': day_event.event_type,
        'eventLabel': day_event.event_label,
        'eventDescription': day_event.event_description,
        'eventTone': day_event.event_tone,
    }


def serialize_slot(slot, current_player, day_event_map=None):
    day_event_map = day_event_map or {}
    event_meta = event_meta_for_day(slot.day_of_week, day_event_map)

    return {
        'id': slot.id,
        'playerId': slot.player_id,
        'slotType': slot.slot_type,
        'eventType': '' if (slot.is_unavailable or slot.is_full_day_available or slot.is_tentative) else event_meta['eventType'],
        'eventLabel': slot.label if (slot.is_unavailable or slot.is_full_day_available or slot.is_tentative) else event_meta['eventLabel'],
        'eventDescription': '' if (slot.is_unavailable or slot.is_full_day_available or slot.is_tentative) else event_meta['eventDescription'],
        'eventTone': (
            'red' if slot.is_unavailable else
            'green' if slot.is_full_day_available else
            'orange' if slot.is_tentative else
            event_meta['eventTone']
        ),
        'dayOfWeek': slot.day_of_week,
        'startTimeMinutes': slot.start_time_minutes,
        'endTimeMinutes': slot.end_time_minutes,
        'startLabel': slot.start_label,
        'endLabel': slot.end_label,
        'timeRange': slot.time_range if slot.is_available else '',
        'label': slot.label if (slot.is_unavailable or slot.is_full_day_available or slot.is_tentative) else event_meta['eventLabel'],
        'note': slot.note,
        'displayNote': slot.note or (slot.label if (slot.is_unavailable or slot.is_full_day_available or slot.is_tentative) else event_meta['eventLabel']),
        'canEdit': current_player == slot.player,
    }


def parse_body(request):
    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return None


def cleaned_profile_payload(payload):
    battle_tags_raw = payload.get('battleTagsText') or ''
    battle_tags = [tag.strip() for tag in battle_tags_raw.splitlines() if tag.strip()]
    return {
        'name': (payload.get('name') or '').strip(),
        'battle_tags': '\n'.join(battle_tags),
    }


def form_data_from_payload(payload):
    return {
        'slot_type': payload.get('slotType') or ScheduleSlot.AVAILABLE,
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
    ensure_current_roster_week()
    current_player = get_current_player(request.user)
    current_staff_member = get_current_staff_member(request.user)
    current_connection = get_discord_connection_for_user(request.user)
    players = list(Player.objects.select_related('user__discord_connection').prefetch_related('slots'))
    staff_members = list(StaffMember.objects.select_related('user__discord_connection'))
    slots = ScheduleSlot.objects.select_related('player').all()
    day_events = list(DayEventType.objects.all())
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
        'days': build_days(),
        'players': [serialize_player(player, current_player) for player in players],
        'staffMembers': [serialize_staff_member(staff_member, current_staff_member) for staff_member in staff_members],
        'slots': [serialize_slot(slot, current_player, day_event_map) for slot in slots],
        'dayEventTypes': [serialize_day_event(day_event) for day_event in day_events],
        'eventTypes': ScheduleSlot.event_types_payload(),
        'lastUpdated': build_timestamp_label(),
    })


def build_timestamp_label():
    return timezone.localtime(BUILD_TIMESTAMP).strftime('%d.%m.%Y %H:%M')


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


@require_http_methods(['PATCH', 'POST'])
@login_required
def profile_update(request):
    current_player = get_current_player(request.user)
    current_staff_member = get_current_staff_member(request.user)
    if current_player is None and current_staff_member is None:
        return JsonResponse({'error': 'Аккаунт не привязан к профилю.'}, status=403)

    payload = parse_body(request)
    if payload is None:
        return JsonResponse({'error': 'Некорректный JSON.'}, status=400)

    profile_data = cleaned_profile_payload(payload)
    if current_player is not None and payload.get('name') is None:
        profile_data['name'] = current_player.name
    elif current_staff_member is not None and payload.get('name') is None:
        profile_data['name'] = current_staff_member.name
    if not profile_data['name']:
        return JsonResponse({'errors': {'name': ['Имя не может быть пустым.']}}, status=400)

    if current_player is not None:
        current_player.name = profile_data['name']
        current_player.battle_tags = profile_data['battle_tags']
        current_player.full_clean()
        current_player.save(update_fields=['name', 'battle_tags'])
        return JsonResponse({
            'profileType': 'player',
            'profile': serialize_player(current_player, current_player),
            'player': serialize_player(current_player, current_player),
        })

    current_staff_member.name = profile_data['name']
    current_staff_member.full_clean()
    current_staff_member.save(update_fields=['name'])
    return JsonResponse({
        'profileType': 'staff',
        'profile': serialize_staff_member(current_staff_member, current_staff_member),
    })


@require_GET
@login_required
def discord_connect(request):
    if not can_manage_profile(request.user):
        return JsonResponse({'error': 'Аккаунт не привязан к профилю.'}, status=403)
    if not discord_oauth_configured():
        return HttpResponseRedirect(build_profile_redirect('error', 'not-configured'))

    state = get_random_string(32)
    request.session[DISCORD_STATE_SESSION_KEY] = state
    query = urlencode({
        'client_id': settings.DISCORD_CLIENT_ID,
        'redirect_uri': settings.DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify',
        'state': state,
        'prompt': 'consent',
    })
    return HttpResponseRedirect(f'{DISCORD_AUTHORIZE_URL}?{query}')


@require_GET
@login_required
def discord_callback(request):
    if not can_manage_profile(request.user):
        return JsonResponse({'error': 'Аккаунт не привязан к профилю.'}, status=403)

    session_state = request.session.pop(DISCORD_STATE_SESSION_KEY, '')
    request_state = request.GET.get('state', '')
    if not session_state or session_state != request_state:
        return HttpResponseRedirect(build_profile_redirect('error', 'invalid-state'))

    if request.GET.get('error'):
        return HttpResponseRedirect(build_profile_redirect('error', request.GET.get('error')))

    code = request.GET.get('code', '')
    if not code:
        return HttpResponseRedirect(build_profile_redirect('error', 'missing-code'))

    if not discord_oauth_configured():
        return HttpResponseRedirect(build_profile_redirect('error', 'not-configured'))

    try:
        access_token = exchange_code_for_token(code)
        if not access_token:
            return HttpResponseRedirect(build_profile_redirect('error', 'oauth-failed'))
        identity = fetch_discord_identity(access_token)
    except requests.RequestException:
        return HttpResponseRedirect(build_profile_redirect('error', 'oauth-failed'))

    discord_user_id = str(identity.get('id') or '').strip()
    username = str(identity.get('username') or '').strip()
    if not discord_user_id or not username:
        return HttpResponseRedirect(build_profile_redirect('error', 'oauth-failed'))

    existing = DiscordConnection.objects.filter(discord_user_id=discord_user_id).exclude(user=request.user).first()
    if existing is not None:
        return HttpResponseRedirect(build_profile_redirect('error', 'already-linked'))

    DiscordConnection.objects.update_or_create(
        user=request.user,
        defaults={
            'discord_user_id': discord_user_id,
            'username': username,
            'global_name': str(identity.get('global_name') or '').strip(),
            'avatar_hash': str(identity.get('avatar') or '').strip(),
        },
    )
    return HttpResponseRedirect(build_profile_redirect('connected'))


@require_POST
@login_required
def discord_disconnect(request):
    if not can_manage_profile(request.user):
        return JsonResponse({'error': 'Аккаунт не привязан к профилю.'}, status=403)

    DiscordConnection.objects.filter(user=request.user).delete()
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@login_required
def change_password(request):
    payload = parse_body(request)
    if payload is None:
        return JsonResponse({'error': 'Некорректный JSON.'}, status=400)

    old_password = payload.get('oldPassword') or ''
    new_password = payload.get('newPassword') or ''
    new_password_confirm = payload.get('newPasswordConfirm') or ''

    errors = {}

    if not request.user.check_password(old_password):
        errors['oldPassword'] = ['Старый пароль указан неверно.']

    if new_password != new_password_confirm:
        errors['newPasswordConfirm'] = ['Новые пароли не совпадают.']

    if not new_password:
        errors.setdefault('newPassword', []).append('Введите новый пароль.')

    if not new_password_confirm:
        errors.setdefault('newPasswordConfirm', []).append('Повторите новый пароль.')

    if not errors:
        try:
            validate_password(new_password, user=request.user)
        except ValidationError as exc:
            errors['newPassword'] = list(exc.messages)

    if errors:
        return JsonResponse({'errors': errors}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])
    update_session_auth_hash(request, request.user)
    return JsonResponse({'ok': True})


@require_POST
@login_required
def logout_view(request):
    logout(request)
    return JsonResponse({'ok': True, 'redirectUrl': '/login/'})
