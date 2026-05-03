from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST

from .api_serializers import serialize_player, serialize_staff_member
from .api_utils import parse_body
from .profile_lookup import get_current_player, get_current_staff_member


def cleaned_profile_payload(payload):
    battle_tags_raw = payload.get('battleTagsText') or ''
    battle_tags = [tag.strip() for tag in battle_tags_raw.splitlines() if tag.strip()]
    return {
        'name': (payload.get('name') or '').strip(),
        'battle_tags': '\n'.join(battle_tags),
    }


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
