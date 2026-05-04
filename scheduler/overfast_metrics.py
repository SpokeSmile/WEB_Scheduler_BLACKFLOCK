# Pure metric helpers for OverFast data. Keep these deterministic and
# database-free so they can be tested separately from fetching and cache writes.
# OverFast exposes the top competitive rank as "ultimate", while the player-
# facing Overwatch rank name is Champion. Keep the API value canonical so cached
# payloads are handled correctly, but show the familiar label in the UI.
RANK_DIVISIONS = ['bronze', 'silver', 'gold', 'platinum', 'diamond', 'master', 'grandmaster', 'ultimate']
RANK_DIVISION_ALIASES = {
    'champion': 'ultimate',
}
RANK_LABELS = {
    'bronze': 'Bronze',
    'silver': 'Silver',
    'gold': 'Gold',
    'platinum': 'Platinum',
    'diamond': 'Diamond',
    'master': 'Master',
    'grandmaster': 'Grandmaster',
    'champion': 'Champion',
    'ultimate': 'Champion',
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


def role_key_for_player(player):
    role = (player.role or '').strip().lower()
    for needle, mapped in ROLE_ALIASES.items():
        if needle in role:
            return mapped
    return ''


def normalize_rank_division(division):
    normalized = (division or '').strip().lower()
    return RANK_DIVISION_ALIASES.get(normalized, normalized)


def rank_score(rank):
    if not rank:
        return None
    division = normalize_rank_division(rank.get('division'))
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


def rank_rating_from_score(score):
    if score is None:
        return None
    max_score = len(RANK_DIVISIONS) * 5 - 1
    normalized_score = max(0, min(float(score), max_score))
    if normalized_score >= max_score:
        return 5000
    # Internal rank score is 0..39. Product rating maps Bronze 5 to 1000 and
    # advances by 100 points per division up to Champion 1 at 5000.
    return round(1000 + normalized_score * 100)


def safe_number(value, default=0):
    return value if isinstance(value, (int, float)) else default


def ratio(numerator, denominator):
    if not denominator:
        return 0
    return round(numerator / denominator, 2)


def hero_label(hero_key):
    return (hero_key or '').replace('-', ' ').replace('_', ' ').title()


def hero_time_played(payload):
    return safe_number(payload.get('time_played'))


def average_eliminations(general):
    average = general.get('average') or {}
    total = general.get('total') or {}
    explicit_average = safe_number(average.get('eliminations'), None)
    if explicit_average is not None:
        return explicit_average
    games_played = safe_number(general.get('games_played'))
    if not games_played:
        return 0
    return round(safe_number(total.get('eliminations')) / games_played, 1)


def rank_distribution(player_rows):
    counts = {division: 0 for division in RANK_DIVISIONS}
    for row in player_rows:
        rank = row.get('rank')
        if rank:
            division = normalize_rank_division(rank['division'])
            if division in counts:
                counts[division] += 1
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
        if cache.status != cache.STATUS_READY:
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
