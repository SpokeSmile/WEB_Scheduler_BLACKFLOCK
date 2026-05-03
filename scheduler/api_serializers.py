import os
from datetime import datetime, timedelta

from django.utils import timezone

from .models import DiscordConnection, ScheduleSlot


def resolve_build_timestamp():
    raw_value = os.environ.get('BUILD_TIMESTAMP')
    if raw_value:
        parsed = datetime.fromisoformat(raw_value.replace('Z', '+00:00'))
        if timezone.is_naive(parsed):
            return timezone.make_aware(parsed)
        return parsed
    return timezone.now()


BUILD_TIMESTAMP = resolve_build_timestamp()


def build_timestamp_label():
    return timezone.localtime(BUILD_TIMESTAMP).strftime('%d.%m.%Y %H:%M')


def get_discord_connection_for_user(user):
    if not user or not getattr(user, 'pk', None):
        return None
    try:
        return user.discord_connection
    except DiscordConnection.DoesNotExist:
        return None


def discord_payload(connection):
    if connection is None:
        return {
            'discordConnected': False,
            'discordUsername': '',
            'discordGlobalName': '',
            'discordDisplayTag': '',
            'avatarUrl': '',
        }
    return {
        'discordConnected': True,
        'discordUsername': connection.username,
        'discordGlobalName': connection.global_name,
        'discordDisplayTag': connection.display_tag,
        'avatarUrl': connection.avatar_url,
    }


def build_days(week_start=None):
    if week_start is None:
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())

    return [
        {
            'value': value,
            'label': label,
            'date': (week_start + timedelta(days=value)).strftime('%d.%m'),
        }
        for value, label in ScheduleSlot.DAY_CHOICES
    ]


def serialize_player(player, current_player):
    payload = discord_payload(player.discord_connection)
    return {
        'id': player.id,
        'name': player.name,
        'role': player.role,
        'roleColor': player.role_color,
        'initial': player.initial,
        'avatarUrl': payload['avatarUrl'],
        'battleTags': player.battle_tags_list,
        'battleTagsText': '\n'.join(player.battle_tags_list),
        'discordConnected': payload['discordConnected'],
        'discordUsername': payload['discordUsername'],
        'discordGlobalName': payload['discordGlobalName'],
        'discordDisplayTag': payload['discordDisplayTag'],
        'canEdit': current_player == player,
    }


def serialize_staff_member(staff_member, current_staff_member=None):
    payload = discord_payload(staff_member.discord_connection)
    return {
        'id': staff_member.id,
        'name': staff_member.name,
        'role': staff_member.role,
        'roleColor': staff_member.role_color,
        'initial': staff_member.initial,
        'avatarUrl': payload['avatarUrl'],
        'discordConnected': payload['discordConnected'],
        'discordUsername': payload['discordUsername'],
        'discordGlobalName': payload['discordGlobalName'],
        'discordDisplayTag': payload['discordDisplayTag'],
        'canEdit': current_staff_member == staff_member,
    }


def serialize_day_event(day_event):
    return {
        'weekStart': day_event.week_start.isoformat(),
        'dayOfWeek': day_event.day_of_week,
        'eventType': day_event.event_type,
        'eventLabel': day_event.event_label,
        'eventDescription': day_event.event_description,
        'eventTone': day_event.event_tone,
    }


def serialize_game_update_summary(game_update):
    return {
        'slug': game_update.slug,
        'title': game_update.title,
        'publishedAt': game_update.published_at.isoformat(),
        'typeLabel': game_update.type_label,
        'summary': game_update.summary,
        'heroImageUrl': game_update.hero_image_url,
        'sourceUrl': game_update.source_url,
    }


def serialize_game_update_detail(game_update):
    payload = serialize_game_update_summary(game_update)
    payload['contentJson'] = game_update.content_json
    return payload


def event_meta_for_day(day_of_week, day_event_map):
    day_event = day_event_map.get(day_of_week)
    if not day_event or not day_event.event_type:
        return {
            'eventType': '',
            'eventLabel': 'Availability',
            'eventDescription': '',
            'eventTone': 'fallback',
        }

    return {
        'eventType': day_event.event_type,
        'eventLabel': day_event.event_label,
        'eventDescription': day_event.event_description,
        'eventTone': day_event.event_tone,
    }


def serialize_slot(slot, current_player, day_event_map=None, can_edit_week=True):
    day_event_map = day_event_map or {}
    event_meta = event_meta_for_day(slot.day_of_week, day_event_map)
    is_all_day_status = slot.is_unavailable or slot.is_full_day_available or slot.is_tentative

    return {
        'id': slot.id,
        'playerId': slot.player_id,
        'weekStart': slot.week_start.isoformat(),
        'slotType': slot.slot_type,
        'eventType': '' if is_all_day_status else event_meta['eventType'],
        'eventLabel': slot.label if is_all_day_status else event_meta['eventLabel'],
        'eventDescription': '' if is_all_day_status else event_meta['eventDescription'],
        'eventTone': (
            'red' if slot.is_unavailable else
            'green' if slot.is_full_day_available else
            'orange' if slot.is_tentative else
            event_meta['eventTone']
        ),
        'dayOfWeek': slot.day_of_week,
        'startTimeMinutes': slot.start_time_minutes,
        'endTimeMinutes': slot.end_time_minutes,
        'startLabel': slot.start_label,
        'endLabel': slot.end_label,
        'timeRange': slot.time_range if slot.is_available else '',
        'label': slot.label if is_all_day_status else event_meta['eventLabel'],
        'note': slot.note,
        'displayNote': slot.note or (slot.label if is_all_day_status else event_meta['eventLabel']),
        'canEdit': can_edit_week and current_player == slot.player,
    }
