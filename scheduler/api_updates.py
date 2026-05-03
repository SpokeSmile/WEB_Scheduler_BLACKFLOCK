from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from .api_serializers import serialize_game_update_detail, serialize_game_update_summary
from .game_updates import GameUpdateSyncError, sync_game_updates
from .models import GameUpdate


def expected_sync_secrets():
    return [value for value in [settings.CRON_SECRET, settings.GAME_UPDATES_SYNC_TOKEN] if value]


def request_has_sync_secret(request):
    authorization = request.headers.get('Authorization', '').strip()
    return any(authorization == f'Bearer {secret}' for secret in expected_sync_secrets())


@require_GET
@login_required
def game_updates_list(request):
    updates = GameUpdate.objects.all()
    return JsonResponse({'updates': [serialize_game_update_summary(item) for item in updates]})


@require_GET
@login_required
def game_update_detail(request, slug):
    game_update = get_object_or_404(GameUpdate, slug=slug)
    return JsonResponse({'update': serialize_game_update_detail(game_update)})


@require_GET
def game_updates_sync(request):
    if not expected_sync_secrets():
        return JsonResponse({'error': 'Sync secret is not configured.'}, status=503)
    if not request_has_sync_secret(request):
        return JsonResponse({'error': 'Unauthorized.'}, status=401)

    try:
        result = sync_game_updates()
    except GameUpdateSyncError as exc:
        return JsonResponse({'error': str(exc)}, status=502)

    return JsonResponse({'ok': True, **result})
