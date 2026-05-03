from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import OverwatchStatsCache
from .overfast import build_overwatch_stats_dashboard, refresh_overwatch_stats


def clean_overwatch_stats_mode(request):
    mode = request.GET.get('mode') or request.POST.get('mode') or OverwatchStatsCache.COMPETITIVE
    if mode != OverwatchStatsCache.COMPETITIVE:
        return OverwatchStatsCache.COMPETITIVE
    return mode


@require_GET
@login_required
def overwatch_stats(request):
    mode = clean_overwatch_stats_mode(request)
    return JsonResponse({'stats': build_overwatch_stats_dashboard(mode)})


@require_POST
@login_required
def overwatch_stats_refresh(request):
    mode = clean_overwatch_stats_mode(request)
    result = refresh_overwatch_stats()
    return JsonResponse({
        'ok': True,
        'refresh': result,
        'stats': build_overwatch_stats_dashboard(mode),
    })
