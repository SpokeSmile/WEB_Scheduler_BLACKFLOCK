from urllib.parse import quote
import time

import requests

# Low-level OverFast HTTP client. Keep this module free of Django model writes;
# it should only translate HTTP/API failures into errors the sync layer can store
# per player.

OVERFAST_BASE_URL = 'https://overfast-api.tekrop.fr'
OVERFAST_TIMEOUT = 18
HERO_PORTRAIT_CACHE_SECONDS = 60 * 60 * 24
_HERO_PORTRAIT_CACHE = {
    'expires_at': 0,
    'items': {},
}


class OverfastError(Exception):
    pass


def normalize_battle_tag(value):
    return (value or '').strip().replace('#', '-')


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


def fetch_overfast_heroes():
    return overfast_get('/heroes')


def get_hero_portrait_map():
    now = time.time()
    cached_items = _HERO_PORTRAIT_CACHE['items']
    if cached_items and _HERO_PORTRAIT_CACHE['expires_at'] > now:
        return cached_items

    try:
        heroes = fetch_overfast_heroes()
    except OverfastError:
        return cached_items

    portraits = {
        hero.get('key'): hero.get('portrait') or ''
        for hero in heroes
        if isinstance(hero, dict) and hero.get('key')
    }
    _HERO_PORTRAIT_CACHE['items'] = portraits
    _HERO_PORTRAIT_CACHE['expires_at'] = now + HERO_PORTRAIT_CACHE_SECONDS
    return portraits
