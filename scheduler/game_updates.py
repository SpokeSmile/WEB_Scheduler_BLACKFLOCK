import json
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.db import transaction
from django.utils.text import slugify

from .models import GameUpdate

# Blizzard exposes patch notes as HTML, not as a stable public JSON feed. The
# parser normalizes that HTML into simple content blocks used by the API/UI.

PATCH_NOTES_URL = 'https://overwatch.blizzard.com/en-us/news/patch-notes/'
SUMMARY_MAX_LENGTH = 320
ARCHIVE_MONTHS_TO_REFRESH = 2


class GameUpdateSyncError(Exception):
    pass


def normalize_text(value):
    return re.sub(r'\s+', ' ', (value or '').strip())


def build_update_slug(published_at, title):
    base = slugify(title)[:150] or 'patch-notes'
    return f'{published_at:%Y-%m-%d}-{base}'


def extract_patch_notes_date_map(html):
    match = re.search(r'patchNotesDates\s*=\s*(\{.*?\});', html, flags=re.S)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def extract_archive_months(html, channel='live'):
    date_map = extract_patch_notes_date_map(html)
    months = date_map.get(channel, [])
    if not isinstance(months, list):
        return []
    return [value for value in months if re.fullmatch(r'\d{4}-\d{2}', str(value or ''))]


def build_archive_url(month_key, channel='live'):
    year, month = month_key.split('-')
    return f'https://overwatch.blizzard.com/en-us/news/patch-notes/{channel}/{year}/{month}'


def classify_update_type(title, blocks):
    heading_texts = ' '.join(
        block['text']
        for block in blocks
        if block.get('type') == 'heading' and block.get('text')
    )
    source = f'{title} {heading_texts}'.lower()

    if 'hotfix' in source:
        return 'Hotfix'
    if 'bug fix' in source:
        return 'Bug Fix'
    if 'season' in source or 'event' in source:
        return 'Season / Event'
    if 'patch notes' in source:
        return 'Patch Notes'
    return 'Update'


def excerpt_text(value, limit=SUMMARY_MAX_LENGTH):
    text = normalize_text(value)
    if len(text) <= limit:
        return text
    trimmed = text[:limit].rsplit(' ', 1)[0].strip()
    return f'{trimmed or text[:limit]}...'


def extract_summary(blocks):
    for block in blocks:
        if block.get('type') == 'paragraph' and block.get('text'):
            return excerpt_text(block['text'])

    for block in blocks:
        if block.get('type') == 'bullet_list' and block.get('items'):
            return excerpt_text(' '.join(block['items']))

    return ''


def heading_level(node):
    if node.name in {'h2', 'h3', 'h4', 'h5', 'h6'}:
        return min(int(node.name[1]), 6)
    return 6


def append_block(blocks, block):
    if not block:
        return
    if block['type'] == 'heading' and not block.get('text'):
        return
    if block['type'] == 'paragraph' and not block.get('text'):
        return
    if block['type'] == 'bullet_list' and not block.get('items'):
        return
    if block['type'] == 'image' and not block.get('src'):
        return

    if blocks and blocks[-1] == block:
        return
    blocks.append(block)


def parse_children(node, blocks):
    for child in getattr(node, 'children', []):
        if getattr(child, 'name', None) is None:
            continue

        classes = set(child.get('class', []))

        # The page mixes generic patch sections and hero ability blocks. Treat
        # both structures as the same small JSON block vocabulary.
        if child.name in {'h2', 'h3', 'h4', 'h5', 'h6'}:
            append_block(blocks, {
                'type': 'heading',
                'level': heading_level(child),
                'text': normalize_text(child.get_text(' ', strip=True)),
            })
            continue

        if child.name == 'p':
            append_block(blocks, {
                'type': 'paragraph',
                'text': normalize_text(child.get_text(' ', strip=True)),
            })
            continue

        if child.name == 'ul':
            items = [
                normalize_text(item.get_text(' ', strip=True))
                for item in child.find_all('li', recursive=False)
                if normalize_text(item.get_text(' ', strip=True))
            ]
            append_block(blocks, {
                'type': 'bullet_list',
                'items': items,
            })
            continue

        if child.name == 'img' and 'PatchNotesHeroUpdate-icon' in classes:
            append_block(blocks, {
                'type': 'image',
                'src': child.get('src', '').strip(),
                'alt': normalize_text(child.get('alt', '')),
            })
            continue

        if classes.intersection({'PatchNotesAbilityUpdate-name', 'PatchNotesGeneralUpdate-title'}):
            append_block(blocks, {
                'type': 'heading',
                'level': 6,
                'text': normalize_text(child.get_text(' ', strip=True)),
            })
            continue

        parse_children(child, blocks)


def build_source_url(patch_node, anchor_id, base_url):
    first_link = patch_node.find('a', href=True)
    if first_link and '/news/patch-notes/' in first_link['href']:
        return urljoin(base_url, first_link['href'])
    if anchor_id:
        return urljoin(base_url, f'#{anchor_id}')
    return base_url


def parse_patch_node(patch_node, base_url=PATCH_NOTES_URL):
    anchor = patch_node.find('div', class_='anchor')
    anchor_id = anchor.get('id', '').strip() if anchor else ''
    date_node = patch_node.find('div', class_='PatchNotes-date')
    title_node = patch_node.find('h3', class_='PatchNotes-patchTitle')
    if date_node is None or title_node is None:
        return None

    date_text = normalize_text(date_node.get_text(' ', strip=True))
    title = normalize_text(title_node.get_text(' ', strip=True))
    published_at = datetime.strptime(date_text, '%B %d, %Y').date()

    blocks = []
    for child in patch_node.find_all(recursive=False):
        child_classes = set(child.get('class', []))
        if child.name in {'h3'} or 'PatchNotesTop' in child_classes or 'PatchNotes-labels' in child_classes or 'anchor' in child_classes:
            continue
        parse_children(child, blocks)

    hero_image = ''
    first_hero_image = patch_node.select_one('img.PatchNotesHeroUpdate-icon[alt]')
    if first_hero_image:
        hero_image = first_hero_image.get('src', '').strip()

    summary = extract_summary(blocks)
    type_label = classify_update_type(title, blocks)

    return {
        'slug': build_update_slug(published_at, title),
        'title': title,
        'published_at': published_at,
        'type_label': type_label,
        'source_url': build_source_url(patch_node, anchor_id, base_url),
        'summary': summary,
        'hero_image_url': hero_image,
        'content_json': blocks,
    }


def parse_game_updates_html(html, base_url=PATCH_NOTES_URL):
    soup = BeautifulSoup(html, 'html.parser')
    patches = []
    for patch_node in soup.select('div.PatchNotes-patch'):
        parsed = parse_patch_node(patch_node, base_url=base_url)
        if parsed is not None:
            patches.append(parsed)
    return patches


def fetch_patch_notes_html(url=PATCH_NOTES_URL):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.text


def collect_patch_payloads(root_html, full_archive=False):
    payloads_by_slug = {}
    visited_urls = {PATCH_NOTES_URL}

    for payload in parse_game_updates_html(root_html):
        payloads_by_slug[payload['slug']] = payload

    archive_months = extract_archive_months(root_html, channel='live')
    months_to_fetch = archive_months if full_archive else archive_months[:ARCHIVE_MONTHS_TO_REFRESH]

    # Normal cron sync is intentionally shallow to keep Vercel execution time
    # predictable. Manual full-archive sync can backfill older months.
    for month_key in months_to_fetch:
        archive_url = build_archive_url(month_key, channel='live')
        if archive_url in visited_urls:
            continue
        visited_urls.add(archive_url)
        archive_html = fetch_patch_notes_html(archive_url)
        for payload in parse_game_updates_html(archive_html, base_url=archive_url):
            payloads_by_slug[payload['slug']] = payload

    return payloads_by_slug


@transaction.atomic
def sync_game_updates(full_archive=False):
    try:
        html = fetch_patch_notes_html()
    except requests.RequestException as exc:
        raise GameUpdateSyncError('Не удалось загрузить patch notes Blizzard.') from exc

    try:
        payloads_by_slug = collect_patch_payloads(html, full_archive=full_archive)
    except requests.RequestException as exc:
        raise GameUpdateSyncError('Не удалось загрузить архив patch notes Blizzard.') from exc

    created = 0
    updated = 0

    for payload in payloads_by_slug.values():
        _obj, was_created = GameUpdate.objects.update_or_create(
            slug=payload['slug'],
            defaults=payload,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        'fetched': len(payloads_by_slug),
        'created': created,
        'updated': updated,
        'total': GameUpdate.objects.count(),
    }
