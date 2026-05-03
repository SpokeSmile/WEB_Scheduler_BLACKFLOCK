from urllib.parse import quote

import requests

OVERFAST_BASE_URL = 'https://overfast-api.tekrop.fr'
OVERFAST_TIMEOUT = 18


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
