from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_GET, require_POST

from .models import DiscordConnection
from .profile_lookup import get_current_player, get_current_staff_member

# Discord OAuth connect endpoints. This is not a Discord login flow: the user
# must already be authenticated, and Discord is only a trusted source for avatar
# and handle data.

DISCORD_AUTHORIZE_URL = 'https://discord.com/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'
DISCORD_USER_URL = 'https://discord.com/api/users/@me'
DISCORD_STATE_SESSION_KEY = 'discord_oauth_state'


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


@require_GET
@login_required
def discord_connect(request):
    if not can_manage_profile(request.user):
        return JsonResponse({'error': 'Аккаунт не привязан к профилю.'}, status=403)
    if not discord_oauth_configured():
        return HttpResponseRedirect(build_profile_redirect('error', 'not-configured'))

    # Keep state in the Django session so the callback can reject forged OAuth
    # responses before exchanging the code for a Discord token.
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

    # A Discord account is a unique identity source and must not silently move
    # from one site user to another.
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
