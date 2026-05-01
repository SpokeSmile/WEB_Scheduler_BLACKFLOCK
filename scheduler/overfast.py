from urllib.parse import quote

import requests
from django.utils import timezone

from .models import OverwatchStatsCache, Player

OVERFAST_BASE_URL = 'https://overfast-api.tekrop.fr'
OVERFAST_TIMEOUT = 18
OVERFAST_MODES = [OverwatchStatsCache.COMPETITIVE, OverwatchStatsCache.QUICKPLAY]
RANK_DIVISIONS = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'master', 'grandmaster', 'champion']
RANK_LABELS = {
    'bronze': 'Bronze',
    'silver': 'Silver',
    'gold': 'Gold',
    'platinum': 'Platinum',
    'diamond': 'Diamond',
    'master': 'Master',
    'grandmaster': 'Grandmaster',
    'champion': 'Champion',
}
ROLE_ALIASES = {
    'tank': 'tank',
    'танк': 'tank',
    'dps': 'damage',
    'damage': 'damage',
    'дд': 'damage',
    'support': 'support',
    'supp': 'support',
    'саппорт': 'support',
    'поддержка': 'support',
}


class OverfastError(Exception):
    pass


def normalize_battle_tag(value):
    return (value or '').strip().replace('#', '-')


def primary_battle_tag(player):
    return player.battle_tags_list[0] if player.battle_tags_list else ''


def role_key_for_player(player):
    role = (player.role or '').strip().lower()
    for needle, mapped in ROLE_ALIASES.items():
        if needle in role:
            return mapped
    return ''


def overfast_get(path, params=None):
    url = f'{OVERFAST_BASE_URL}{path}'
    try:
        response = requests.get(url, params=params or {}, timeout=OVERFAST_TIMEOUT)
    except requests.Timeout as exc:
        raise OverfastError('OverFast API timeout.') from exc
    except requests.RequestException as exc:
        raise OverfastError('OverFast API недоступен.') from exc

    if response.status_code == 404:
        raise OverfastError('Профиль не найден или закрыт.')
    if response.status_code == 429:
        raise OverfastError('OverFast API rate limit. Повторите позже.')
    if response.status_code == 503:
        raise OverfastError('Blizzard временно ограничивает статистику. Повторите позже.')
    if response.status_code >= 500:
        raise OverfastError('OverFast API временно не отвечает.')
    if response.status_code >= 400:
        raise OverfastError('Не удалось получить статистику OverFast.')

    try:
        return response.json()
    except ValueError as exc:
        raise OverfastError('OverFast API вернул некорректный JSON.') from exc


def fetch_overfast_summary(player_id):
    return overfast_get(f'/players/{quote(player_id)}/summary')


def fetch_overfast_stats(player_id, mode):
    return overfast_get(
        f'/players/{quote(player_id)}/stats/summary',
        params={'gamemode': mode, 'platform': 'pc'},
    )


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


def rank_score(rank):
    if not rank:
        return None
    division = (rank.get('division') or '').lower()
    tier = rank.get('tier')
    if division not in RANK_DIVISIONS or not isinstance(tier, int):
        return None
    if tier < 1 or tier > 5:
        return None
    return RANK_DIVISIONS.index(division) * 5 + (5 - tier)


def rank_label_from_score(score):
    if score is None:
        return '—'
    normalized = max(0, min(round(score), len(RANK_DIVISIONS) * 5 - 1))
    division = RANK_DIVISIONS[normalized // 5]
    tier = 5 - (normalized % 5)
    return f'{RANK_LABELS[division]} {tier}'


def serialize_rank(rank, role=''):
    score = rank_score(rank)
    if score is None:
        return None
    division = (rank.get('division') or '').lower()
    tier = rank.get('tier')
    return {
        'division': division,
        'divisionLabel': RANK_LABELS.get(division, division.title()),
        'tier': tier,
        'label': f'{RANK_LABELS.get(division, division.title())} {tier}',
        'role': role,
        'rankIcon': rank.get('rank_icon') or '',
        'roleIcon': rank.get('role_icon') or '',
        'score': score,
    }


def select_rank(summary, player):
    competitive = (summary or {}).get('competitive') or {}
    platform_ranks = competitive.get('pc') or {}
    preferred_role = role_key_for_player(player)
    if preferred_role and platform_ranks.get(preferred_role):
        return serialize_rank(platform_ranks[preferred_role], preferred_role)

    ranked_roles = []
    for role in ['tank', 'damage', 'support', 'open']:
        serialized = serialize_rank(platform_ranks.get(role), role)
        if serialized:
            ranked_roles.append(serialized)
    if not ranked_roles:
        return None
    return max(ranked_roles, key=lambda item: item['score'])


def safe_number(value, default=0):
    return value if isinstance(value, (int, float)) else default


def ratio(numerator, denominator):
    if not denominator:
        return 0
    return round(numerator / denominator, 2)


def hero_label(hero_key):
    return (hero_key or '').replace('-', ' ').replace('_', ' ').title()


def serialize_player_row(player, cache):
    status = cache.status if cache else OverwatchStatsCache.STATUS_ERROR
    stats = cache.stats_json if cache and cache.stats_json else {}
    summary = cache.summary_json if cache and cache.summary_json else {}
    general = stats.get('general') or {}
    total = general.get('total') or {}
    average = general.get('average') or {}
    wins = safe_number(general.get('games_won'))
    losses = safe_number(general.get('games_lost'))
    deaths = safe_number(total.get('deaths'))
    eliminations = safe_number(total.get('eliminations'))
    rank = select_rank(summary, player)
    connection = player.discord_connection

    return {
        'id': player.id,
        'name': player.name,
        'role': player.role,
        'roleColor': player.role_color,
        'avatarUrl': connection.avatar_url if connection else '',
        'battleTag': cache.battle_tag if cache else primary_battle_tag(player),
        'playerId': cache.overfast_player_id if cache else normalize_battle_tag(primary_battle_tag(player)),
        'status': status,
        'error': cache.error if cache else 'Данные еще не загружены.',
        'updatedAt': cache.fetched_at.isoformat() if cache and cache.fetched_at else '',
        'rank': rank,
        'sr': None,
        'winrate': safe_number(general.get('winrate')),
        'matches': safe_number(general.get('games_played')),
        'wins': wins,
        'losses': losses,
        'timePlayed': safe_number(general.get('time_played')),
        'kd': ratio(eliminations, deaths),
        'avgDamage': safe_number(average.get('damage')),
        'avgDeaths': safe_number(average.get('deaths')),
        'recentGamesAvailable': False,
        'recentGamesLabel': 'Недоступно',
    }


def aggregate_top_heroes(caches):
    heroes = {}
    for cache in caches:
        if cache.status != OverwatchStatsCache.STATUS_READY:
            continue
        for hero_key, payload in (cache.stats_json.get('heroes') or {}).items():
            entry = heroes.setdefault(hero_key, {
                'hero': hero_key,
                'heroLabel': hero_label(hero_key),
                'matches': 0,
                'wins': 0,
                'losses': 0,
                'damageTotal': 0,
                'damageSamples': 0,
            })
            matches = safe_number(payload.get('games_played'))
            wins = safe_number(payload.get('games_won'))
            losses = safe_number(payload.get('games_lost'))
            avg_damage = safe_number((payload.get('average') or {}).get('damage'))
            entry['matches'] += matches
            entry['wins'] += wins
            entry['losses'] += losses
            if matches:
                entry['damageTotal'] += avg_damage * matches
                entry['damageSamples'] += matches

    rows = []
    for entry in heroes.values():
        matches = entry['matches']
        rows.append({
            'hero': entry['hero'],
            'heroLabel': entry['heroLabel'],
            'matches': matches,
            'wins': entry['wins'],
            'losses': entry['losses'],
            'winrate': round((entry['wins'] / matches) * 100, 1) if matches else 0,
            'avgDamage': round(entry['damageTotal'] / entry['damageSamples'], 1) if entry['damageSamples'] else 0,
        })
    return sorted(rows, key=lambda item: (item['matches'], item['winrate']), reverse=True)[:5]


def rank_distribution(player_rows):
    counts = {division: 0 for division in RANK_DIVISIONS}
    for row in player_rows:
        rank = row.get('rank')
        if rank:
            counts[rank['division']] += 1
    return [
        {'division': division, 'divisionLabel': RANK_LABELS[division], 'count': counts[division]}
        for division in reversed(RANK_DIVISIONS)
    ]


def weighted_mode_summary(caches):
    wins = 0
    losses = 0
    matches = 0
    time_played = 0
    for cache in caches:
        if cache.status != OverwatchStatsCache.STATUS_READY:
            continue
        general = (cache.stats_json or {}).get('general') or {}
        wins += safe_number(general.get('games_won'))
        losses += safe_number(general.get('games_lost'))
        matches += safe_number(general.get('games_played'))
        time_played += safe_number(general.get('time_played'))
    return {
        'wins': wins,
        'losses': losses,
        'matches': matches,
        'timePlayed': time_played,
        'winrate': round((wins / (wins + losses)) * 100, 1) if wins + losses else 0,
    }


def build_overwatch_stats_dashboard(mode=OverwatchStatsCache.COMPETITIVE):
    if mode not in OVERFAST_MODES:
        mode = OverwatchStatsCache.COMPETITIVE

    players = list(Player.objects.select_related('user__discord_connection').order_by('sort_order', 'id'))
    caches = list(OverwatchStatsCache.objects.select_related('player').filter(player__in=players))
    cache_map = {(cache.player_id, cache.mode): cache for cache in caches}
    selected_caches = [cache for cache in caches if cache.mode == mode]
    rows = [
        serialize_player_row(player, cache_map.get((player.id, mode)))
        for player in players
    ]
    team_summary = weighted_mode_summary(selected_caches)
    rank_scores = [row['rank']['score'] for row in rows if row.get('rank')]
    team_summary.update({
        'averageRank': rank_label_from_score(sum(rank_scores) / len(rank_scores)) if rank_scores else '—',
        'averageRankScore': round(sum(rank_scores) / len(rank_scores), 1) if rank_scores else None,
        'bestStreak': 'Недоступно',
        'worstStreak': 'Недоступно',
        'unavailablePlayers': len([row for row in rows if row['status'] != OverwatchStatsCache.STATUS_READY]),
    })

    winrate_by_mode = []
    for item_mode, label in [(OverwatchStatsCache.COMPETITIVE, 'Competitive'), (OverwatchStatsCache.QUICKPLAY, 'Quickplay')]:
        summary = weighted_mode_summary([cache for cache in caches if cache.mode == item_mode])
        winrate_by_mode.append({'mode': item_mode, 'label': label, 'winrate': summary['winrate'], 'matches': summary['matches']})

    latest_cache = max([cache for cache in caches if cache.fetched_at], key=lambda item: item.fetched_at, default=None)

    return {
        'mode': mode,
        'period': {'value': 'all_time', 'label': 'All-time'},
        'platform': 'pc',
        'updatedAt': latest_cache.fetched_at.isoformat() if latest_cache else '',
        'cacheEmpty': not caches,
        'players': rows,
        'team': team_summary,
        'rankDistribution': rank_distribution(rows),
        'winrateByMode': winrate_by_mode,
        'topHeroes': aggregate_top_heroes(selected_caches),
        'unavailableMessage': 'История матчей, серии и настоящий SR недоступны в OverFast API.',
    }
