from django.utils import timezone

from .models import OverwatchStatsCache, Player
from .overfast_client import (
    OverfastError,
    fetch_overfast_stats,
    fetch_overfast_summary,
    normalize_battle_tag,
)

OVERFAST_MODES = [OverwatchStatsCache.COMPETITIVE]

# The sync is deliberately sequential. That is slower, but kinder to OverFast and
# keeps partial failures isolated to one player instead of failing the dashboard.


def primary_battle_tag(player):
    return player.battle_tags_list[0] if player.battle_tags_list else ''


def cache_missing_battletag(player, now):
    for mode in OVERFAST_MODES:
        OverwatchStatsCache.objects.update_or_create(
            player=player,
            mode=mode,
            defaults={
                'battle_tag': '',
                'overfast_player_id': '',
                'status': OverwatchStatsCache.STATUS_MISSING_BATTLETAG,
                'error': 'BattleTag не указан.',
                'summary_json': {},
                'stats_json': {},
                'fetched_at': now,
            },
        )


def cache_error(player, battle_tag, player_id, mode, summary, message, now):
    OverwatchStatsCache.objects.update_or_create(
        player=player,
        mode=mode,
        defaults={
            'battle_tag': battle_tag,
            'overfast_player_id': player_id,
            'status': OverwatchStatsCache.STATUS_ERROR,
            'error': message,
            'summary_json': summary or {},
            'stats_json': {},
            'fetched_at': now,
        },
    )


def cache_ready(player, battle_tag, player_id, mode, summary, stats, now):
    OverwatchStatsCache.objects.update_or_create(
        player=player,
        mode=mode,
        defaults={
            'battle_tag': battle_tag,
            'overfast_player_id': player_id,
            'status': OverwatchStatsCache.STATUS_READY,
            'error': '',
            'summary_json': summary or {},
            'stats_json': stats or {},
            'fetched_at': now,
        },
    )


def refresh_overwatch_stats(players=None):
    players = list(players if players is not None else Player.objects.all())
    now = timezone.now()
    result = {'players': len(players), 'updated': 0, 'errors': 0, 'missingBattleTags': 0}

    for player in players:
        # Product rule: only the first BattleTag is authoritative for stats v1.
        battle_tag = primary_battle_tag(player)
        player_id = normalize_battle_tag(battle_tag)
        if not player_id:
            cache_missing_battletag(player, now)
            result['missingBattleTags'] += 1
            continue

        try:
            summary = fetch_overfast_summary(player_id)
        except OverfastError as exc:
            for mode in OVERFAST_MODES:
                cache_error(player, battle_tag, player_id, mode, {}, str(exc), now)
                result['errors'] += 1
            continue

        for mode in OVERFAST_MODES:
            try:
                stats = fetch_overfast_stats(player_id, mode)
            except OverfastError as exc:
                cache_error(player, battle_tag, player_id, mode, summary, str(exc), now)
                result['errors'] += 1
                continue
            cache_ready(player, battle_tag, player_id, mode, summary, stats, now)
            result['updated'] += 1

    return result
