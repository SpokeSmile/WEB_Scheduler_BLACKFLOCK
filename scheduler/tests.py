from datetime import date
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin import PlayerAdmin, PlayerInline, StaffMemberAdmin
from .forms import ScheduleSlotForm
from .models import DayEventType, DiscordConnection, Player, RosterState, ScheduleSlot, StaffMember
from .roster import ensure_current_roster_week


class ScheduleFormTests(TestCase):
    def test_allows_end_time_2400(self):
        DayEventType.objects.update_or_create(
            day_of_week=ScheduleSlot.MONDAY,
            defaults={'event_type': ScheduleSlot.SCRIM},
        )
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.AVAILABLE,
            'day_of_week': ScheduleSlot.MONDAY,
            'start_time_minutes': 1380,
            'end_time_minutes': 1440,
            'note': 'Поздняя тренировка',
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_rejects_end_before_or_equal_start(self):
        DayEventType.objects.update_or_create(
            day_of_week=ScheduleSlot.MONDAY,
            defaults={'event_type': ScheduleSlot.COMPETITIVE},
        )
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.AVAILABLE,
            'day_of_week': ScheduleSlot.MONDAY,
            'start_time_minutes': 1080,
            'end_time_minutes': 1080,
            'note': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('end_time_minutes', form.errors)

    def test_allows_available_without_day_event_type(self):
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.AVAILABLE,
            'day_of_week': ScheduleSlot.TUESDAY,
            'start_time_minutes': 1080,
            'end_time_minutes': 1200,
            'note': '',
        })

        self.assertTrue(form.is_valid(), form.errors)

    def test_allows_unavailable_without_time(self):
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.UNAVAILABLE,
            'day_of_week': ScheduleSlot.FRIDAY,
            'note': 'Не смогу играть',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['start_time_minutes'])
        self.assertIsNone(form.cleaned_data['end_time_minutes'])

    def test_allows_full_day_available_without_time(self):
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.FULL_DAY_AVAILABLE,
            'day_of_week': ScheduleSlot.THURSDAY,
            'note': 'Буду онлайн весь день',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['start_time_minutes'])
        self.assertIsNone(form.cleaned_data['end_time_minutes'])

    def test_allows_tentative_without_time(self):
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.TENTATIVE,
            'day_of_week': ScheduleSlot.WEDNESDAY,
            'note': 'Пока не уверен',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['start_time_minutes'])
        self.assertIsNone(form.cleaned_data['end_time_minutes'])


class ScheduleAccessTests(TestCase):
    def setUp(self):
        self.player_one = Player.objects.get(name='Игрок 1')
        self.player_two = Player.objects.get(name='Игрок 2')
        self.user_one = User.objects.create_user(username='player1', password='secret-pass')
        self.user_two = User.objects.create_user(username='player2', password='secret-pass')
        self.player_one.user = self.user_one
        self.player_one.save()
        self.player_two.user = self.user_two
        self.player_two.save()

    def test_schedule_requires_login(self):
        response = self.client.get(reverse('schedule'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_schedule_shows_player_role(self):
        self.player_one.role = 'Leader'
        self.player_one.save()
        self.client.login(username='player1', password='secret-pass')
        response = self.client.get(reverse('api_bootstrap'))
        self.assertContains(response, 'Leader')

    def test_player_can_create_own_slot(self):
        DayEventType.objects.update_or_create(
            day_of_week=ScheduleSlot.TUESDAY,
            defaults={'event_type': ScheduleSlot.SCRIM},
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.client.post(reverse('slot_create'), {
            'slot_type': ScheduleSlot.AVAILABLE,
            'day_of_week': ScheduleSlot.TUESDAY,
            'start_time_minutes': 540,
            'end_time_minutes': 1080,
            'note': 'Скримы',
        })

        self.assertRedirects(response, reverse('schedule'))
        self.assertTrue(ScheduleSlot.objects.filter(player=self.player_one).exists())
        self.assertFalse(ScheduleSlot.objects.filter(player=self.player_two).exists())

    def test_player_can_create_unavailable_day(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.client.post(reverse('slot_create'), {
            'slot_type': ScheduleSlot.UNAVAILABLE,
            'day_of_week': ScheduleSlot.FRIDAY,
            'note': 'Не могу в этот день',
        })

        self.assertRedirects(response, reverse('schedule'))
        slot = ScheduleSlot.objects.get(player=self.player_one, day_of_week=ScheduleSlot.FRIDAY)
        self.assertEqual(slot.slot_type, ScheduleSlot.UNAVAILABLE)
        self.assertIsNone(slot.start_time_minutes)
        self.assertIsNone(slot.end_time_minutes)

    def test_player_can_create_full_day_available(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.client.post(reverse('slot_create'), {
            'slot_type': ScheduleSlot.FULL_DAY_AVAILABLE,
            'day_of_week': ScheduleSlot.THURSDAY,
            'note': 'Весь день свободен',
        })

        self.assertRedirects(response, reverse('schedule'))
        slot = ScheduleSlot.objects.get(player=self.player_one, day_of_week=ScheduleSlot.THURSDAY)
        self.assertEqual(slot.slot_type, ScheduleSlot.FULL_DAY_AVAILABLE)
        self.assertIsNone(slot.start_time_minutes)
        self.assertIsNone(slot.end_time_minutes)

    def test_player_can_create_tentative_day(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.client.post(reverse('slot_create'), {
            'slot_type': ScheduleSlot.TENTATIVE,
            'day_of_week': ScheduleSlot.WEDNESDAY,
            'note': 'Пока не уверен',
        })

        self.assertRedirects(response, reverse('schedule'))
        slot = ScheduleSlot.objects.get(player=self.player_one, day_of_week=ScheduleSlot.WEDNESDAY)
        self.assertEqual(slot.slot_type, ScheduleSlot.TENTATIVE)
        self.assertIsNone(slot.start_time_minutes)
        self.assertIsNone(slot.end_time_minutes)

    def test_schedule_marks_unavailable_day(self):
        ScheduleSlot.objects.create(
            player=self.player_one,
            slot_type=ScheduleSlot.UNAVAILABLE,
            day_of_week=ScheduleSlot.SATURDAY,
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.client.get(reverse('schedule'))

        self.assertContains(response, 'root')
        response = self.client.get(reverse('api_bootstrap'))
        data = response.json()
        self.assertTrue(any(slot['slotType'] == ScheduleSlot.UNAVAILABLE for slot in data['slots']))
        self.assertTrue(any(slot['label'] == 'Не могу в этот день' for slot in data['slots']))

    def test_player_cannot_edit_another_players_slot(self):
        slot = ScheduleSlot.objects.create(
            player=self.player_two,
            day_of_week=ScheduleSlot.WEDNESDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.client.post(reverse('slot_edit', args=[slot.pk]), {
            'slot_type': ScheduleSlot.AVAILABLE,
            'day_of_week': ScheduleSlot.THURSDAY,
            'start_time_minutes': 720,
            'end_time_minutes': 840,
            'note': 'Попытка изменения',
        })

        self.assertEqual(response.status_code, 404)
        slot.refresh_from_db()
        self.assertEqual(slot.player, self.player_two)
        self.assertEqual(slot.day_of_week, ScheduleSlot.WEDNESDAY)

    def test_player_cannot_edit_another_players_unavailable_slot(self):
        slot = ScheduleSlot.objects.create(
            player=self.player_two,
            slot_type=ScheduleSlot.UNAVAILABLE,
            day_of_week=ScheduleSlot.SUNDAY,
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.client.post(reverse('slot_edit', args=[slot.pk]), {
            'slot_type': ScheduleSlot.AVAILABLE,
            'day_of_week': ScheduleSlot.SUNDAY,
            'start_time_minutes': 720,
            'end_time_minutes': 840,
            'note': 'Попытка изменения',
        })

        self.assertEqual(response.status_code, 404)
        slot.refresh_from_db()
        self.assertEqual(slot.slot_type, ScheduleSlot.UNAVAILABLE)
        self.assertIsNone(slot.start_time_minutes)


class ScheduleApiTests(TestCase):
    def setUp(self):
        self.player_one = Player.objects.get(name='Игрок 1')
        self.player_two = Player.objects.get(name='Игрок 2')
        self.user_one = User.objects.create_user(username='player1', password='secret-pass')
        self.user_two = User.objects.create_user(username='player2', password='secret-pass')
        self.player_one.user = self.user_one
        self.player_one.role = 'Leader'
        self.player_one.save()
        self.player_two.user = self.user_two
        self.player_two.save()

    def post_json(self, url_name, payload, args=None):
        return self.client.post(
            reverse(url_name, args=args or []),
            data=payload,
            content_type='application/json',
        )

    def patch_json(self, url_name, payload, args=None):
        return self.client.patch(
            reverse(url_name, args=args or []),
            data=payload,
            content_type='application/json',
        )

    def test_bootstrap_returns_roster_data(self):
        DayEventType.objects.update_or_create(
            day_of_week=ScheduleSlot.MONDAY,
            defaults={'event_type': ScheduleSlot.SCRIM},
        )
        self.player_one.battle_tags = 'BlackFlock#1111\nAltBird#2222'
        self.player_one.role_color = '#123456'
        self.player_one.save()
        staff_member = StaffMember.objects.create(
            name='Coach Raven',
            role='Coach',
            role_color='#f3701e',
            sort_order=1,
        )
        DiscordConnection.objects.create(
            user=self.user_one,
            discord_user_id='1001',
            username='blackflock_main',
            global_name='Black Flock Main',
            avatar_hash='avatarhash',
        )
        staff_user = User.objects.create_user(username='coach', password='secret-pass')
        staff_member.user = staff_user
        staff_member.save(update_fields=['user'])
        DiscordConnection.objects.create(
            user=staff_user,
            discord_user_id='2002',
            username='coach_raven',
            global_name='Coach Raven',
            avatar_hash='coachhash',
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user']['username'], 'player1')
        self.assertTrue(any(player['role'] == 'Leader' for player in data['players']))
        self.assertTrue(any(player['roleColor'] == '#123456' for player in data['players']))
        self.assertTrue(any(player['discordDisplayTag'] == '@blackflock_main' for player in data['players']))
        self.assertTrue(any(player['battleTags'] == ['BlackFlock#1111', 'AltBird#2222'] for player in data['players']))
        self.assertTrue(any(staff_member['role'] == 'Coach' for staff_member in data['staffMembers']))
        self.assertTrue(any(staff_member['discordDisplayTag'] == '@coach_raven' for staff_member in data['staffMembers']))
        self.assertTrue(any(event_type['value'] == ScheduleSlot.SCRIM for event_type in data['eventTypes']))
        self.assertTrue(any(day_event['eventType'] == ScheduleSlot.SCRIM for day_event in data['dayEventTypes']))

    def test_bootstrap_returns_players_in_admin_order(self):
        Player.objects.exclude(pk__in=[self.player_one.pk, self.player_two.pk]).update(sort_order=10)
        self.player_one.sort_order = 5
        self.player_one.save()
        self.player_two.sort_order = 1
        self.player_two.save()
        self.client.login(username='player1', password='secret-pass')

        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        players = response.json()['players']
        self.assertEqual(players[0]['id'], self.player_two.id)
        self.assertEqual(players[1]['id'], self.player_one.id)

    def test_api_creates_event_using_day_type(self):
        DayEventType.objects.update_or_create(
            day_of_week=ScheduleSlot.SATURDAY,
            defaults={'event_type': ScheduleSlot.TOURNAMENT},
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_slot_create', {
            'slotType': ScheduleSlot.AVAILABLE,
            'dayOfWeek': ScheduleSlot.SATURDAY,
            'startTimeMinutes': 1200,
            'endTimeMinutes': 1380,
            'note': '',
        })

        self.assertEqual(response.status_code, 201)
        slot = ScheduleSlot.objects.get(player=self.player_one, day_of_week=ScheduleSlot.SATURDAY)
        self.assertEqual(response.json()['slot']['eventType'], ScheduleSlot.TOURNAMENT)
        self.assertEqual(response.json()['slot']['eventLabel'], 'Tournament')

    def test_api_allows_available_without_day_event_type(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_slot_create', {
            'slotType': ScheduleSlot.AVAILABLE,
            'dayOfWeek': ScheduleSlot.SATURDAY,
            'startTimeMinutes': 1200,
            'endTimeMinutes': 1380,
            'note': '',
        })

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['slot']['eventLabel'], 'Availability')

    def test_api_creates_unavailable_day(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_slot_create', {
            'slotType': ScheduleSlot.UNAVAILABLE,
            'dayOfWeek': ScheduleSlot.FRIDAY,
            'note': 'Не могу',
        })

        self.assertEqual(response.status_code, 201)
        slot = ScheduleSlot.objects.get(player=self.player_one, day_of_week=ScheduleSlot.FRIDAY)
        self.assertEqual(slot.slot_type, ScheduleSlot.UNAVAILABLE)
        self.assertIsNone(slot.start_time_minutes)

    def test_api_creates_full_day_available(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_slot_create', {
            'slotType': ScheduleSlot.FULL_DAY_AVAILABLE,
            'dayOfWeek': ScheduleSlot.THURSDAY,
            'note': 'Свободен',
        })

        self.assertEqual(response.status_code, 201)
        slot = ScheduleSlot.objects.get(player=self.player_one, day_of_week=ScheduleSlot.THURSDAY)
        self.assertEqual(slot.slot_type, ScheduleSlot.FULL_DAY_AVAILABLE)
        self.assertIsNone(slot.start_time_minutes)
        self.assertEqual(response.json()['slot']['label'], 'Свободен весь день')
        self.assertEqual(response.json()['slot']['eventTone'], 'green')

    def test_api_creates_tentative_day(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_slot_create', {
            'slotType': ScheduleSlot.TENTATIVE,
            'dayOfWeek': ScheduleSlot.TUESDAY,
            'note': 'Под вопросом',
        })

        self.assertEqual(response.status_code, 201)
        slot = ScheduleSlot.objects.get(player=self.player_one, day_of_week=ScheduleSlot.TUESDAY)
        self.assertEqual(slot.slot_type, ScheduleSlot.TENTATIVE)
        self.assertIsNone(slot.start_time_minutes)
        self.assertEqual(response.json()['slot']['label'], 'Не уверен')
        self.assertEqual(response.json()['slot']['eventTone'], 'orange')

    def test_api_prevents_editing_another_players_slot(self):
        slot = ScheduleSlot.objects.create(
            player=self.player_two,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.patch_json('api_slot_update', {
            'slotType': ScheduleSlot.AVAILABLE,
            'dayOfWeek': ScheduleSlot.MONDAY,
            'startTimeMinutes': 720,
            'endTimeMinutes': 840,
            'note': '',
        }, args=[slot.pk])

        self.assertEqual(response.status_code, 404)
        slot.refresh_from_db()
        self.assertEqual(slot.start_time_minutes, 600)

    def test_api_updates_own_profile(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.patch_json('api_profile_update', {
            'name': 'BlackFlock Main',
            'battleTagsText': 'BlackFlock#1111\nAltBird#2222',
            'discordTag': 'blackflock_main',
        })

        self.assertEqual(response.status_code, 200)
        self.player_one.refresh_from_db()
        self.assertEqual(self.player_one.name, 'BlackFlock Main')
        self.assertEqual(self.player_one.battle_tags_list, ['BlackFlock#1111', 'AltBird#2222'])
        self.assertEqual(self.player_one.discord_tag, '')
        self.assertEqual(response.json()['player']['discordDisplayTag'], '')

    def test_api_changes_password_with_old_password(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_profile_password', {
            'oldPassword': 'secret-pass',
            'newPassword': 'new-strong-secret-123',
            'newPasswordConfirm': 'new-strong-secret-123',
        })

        self.assertEqual(response.status_code, 200)
        self.user_one.refresh_from_db()
        self.assertTrue(self.user_one.check_password('new-strong-secret-123'))

    def test_api_rejects_password_change_with_wrong_old_password(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_profile_password', {
            'oldPassword': 'wrong-pass',
            'newPassword': 'new-strong-secret-123',
            'newPasswordConfirm': 'new-strong-secret-123',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('oldPassword', response.json()['errors'])


class StaffProfileTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(username='coach', password='secret-pass')
        self.staff_member = StaffMember.objects.create(
            name='Coach Raven',
            role='Coach',
            role_color='#f3701e',
            sort_order=1,
            user=self.staff_user,
        )

    def patch_json(self, url_name, payload, args=None):
        return self.client.patch(
            reverse(url_name, args=args or []),
            data=payload,
            content_type='application/json',
        )

    def post_json(self, url_name, payload, args=None):
        return self.client.post(
            reverse(url_name, args=args or []),
            data=payload,
            content_type='application/json',
        )

    def test_bootstrap_returns_staff_profile_identity(self):
        self.client.login(username='coach', password='secret-pass')

        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user']['profileType'], 'staff')
        self.assertEqual(data['user']['staffMemberId'], self.staff_member.id)
        serialized_staff = next(item for item in data['staffMembers'] if item['id'] == self.staff_member.id)
        self.assertTrue(serialized_staff['canEdit'])

    def test_staff_can_update_own_profile(self):
        self.client.login(username='coach', password='secret-pass')

        response = self.patch_json('api_profile_update', {
            'name': 'Coach Nova',
            'discordTag': 'coach_nova',
        })

        self.assertEqual(response.status_code, 200)
        self.staff_member.refresh_from_db()
        self.assertEqual(self.staff_member.name, 'Coach Nova')
        self.assertEqual(self.staff_member.discord_tag, '')
        self.assertEqual(response.json()['profileType'], 'staff')
        self.assertEqual(response.json()['profile']['discordDisplayTag'], '')

    def test_staff_can_change_password(self):
        self.client.login(username='coach', password='secret-pass')

        response = self.post_json('api_profile_password', {
            'oldPassword': 'secret-pass',
            'newPassword': 'new-strong-secret-123',
            'newPasswordConfirm': 'new-strong-secret-123',
        })

        self.assertEqual(response.status_code, 200)
        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.check_password('new-strong-secret-123'))

    def test_staff_and_player_cannot_share_same_user(self):
        shared_user = User.objects.create_user(username='shared-user', password='secret-pass')
        player = Player.objects.get(name='Игрок 1')
        player.user = shared_user
        player.save()

        staff_member = StaffMember(
            name='Manager Crow',
            role='Manager',
            user=shared_user,
        )

        with self.assertRaises(ValidationError):
            staff_member.full_clean()


@override_settings(
    DISCORD_CLIENT_ID='discord-client-id',
    DISCORD_CLIENT_SECRET='discord-client-secret',
    DISCORD_REDIRECT_URI='http://testserver/api/discord/callback/',
)
class DiscordConnectionTests(TestCase):
    def setUp(self):
        player = Player.objects.get(name='Игрок 1')
        user = User.objects.create_user(username='avatar-user', password='secret-pass')
        player.user = user
        player.avatar_data = b'avatar-binary'
        player.avatar_content_type = 'image/png'
        player.save()
        self.player = player
        self.user = user

    def test_bootstrap_ignores_legacy_avatar_without_discord_connection(self):
        self.client.login(username='avatar-user', password='secret-pass')

        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        avatar_url = next(item['avatarUrl'] for item in response.json()['players'] if item['id'] == self.player.id)
        self.assertEqual(avatar_url, '')

    def test_bootstrap_returns_discord_avatar_when_connected(self):
        DiscordConnection.objects.create(
            user=self.user,
            discord_user_id='3003',
            username='avatar-user',
            global_name='Avatar User',
            avatar_hash='avatarhash',
        )
        self.client.login(username='avatar-user', password='secret-pass')

        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        avatar_url = next(item['avatarUrl'] for item in data['players'] if item['id'] == self.player.id)
        self.assertIn('/avatars/3003/avatarhash.png', avatar_url)
        self.assertEqual(data['user']['discordDisplayTag'], '@avatar-user')

    def test_connect_redirects_to_discord_authorize(self):
        self.client.login(username='avatar-user', password='secret-pass')

        response = self.client.get(reverse('api_discord_connect'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('discord.com/oauth2/authorize', response['Location'])

    @patch('scheduler.api.requests.get')
    @patch('scheduler.api.requests.post')
    def test_callback_connects_player_discord(self, mocked_post, mocked_get):
        mocked_post.return_value = Mock(status_code=200)
        mocked_post.return_value.raise_for_status = Mock()
        mocked_post.return_value.json.return_value = {'access_token': 'discord-token'}
        mocked_get.return_value = Mock(status_code=200)
        mocked_get.return_value.raise_for_status = Mock()
        mocked_get.return_value.json.return_value = {
            'id': '4444',
            'username': 'blackflock_player',
            'global_name': 'Black Flock Player',
            'avatar': 'hash4444',
        }
        self.client.login(username='avatar-user', password='secret-pass')
        connect_response = self.client.get(reverse('api_discord_connect'))
        self.assertEqual(connect_response.status_code, 302)
        state = self.client.session['discord_oauth_state']

        response = self.client.get(reverse('api_discord_callback'), {'code': 'oauth-code', 'state': state})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/profile/?discord=connected')
        connection = DiscordConnection.objects.get(user=self.user)
        self.assertEqual(connection.discord_user_id, '4444')
        self.assertEqual(connection.username, 'blackflock_player')
        self.assertEqual(connection.global_name, 'Black Flock Player')
        self.assertEqual(connection.avatar_hash, 'hash4444')

    @patch('scheduler.api.requests.get')
    @patch('scheduler.api.requests.post')
    def test_callback_connects_staff_discord(self, mocked_post, mocked_get):
        staff_user = User.objects.create_user(username='coach', password='secret-pass')
        staff_member = StaffMember.objects.create(
            name='Coach Raven',
            role='Coach',
            user=staff_user,
        )
        mocked_post.return_value = Mock(status_code=200)
        mocked_post.return_value.raise_for_status = Mock()
        mocked_post.return_value.json.return_value = {'access_token': 'discord-token'}
        mocked_get.return_value = Mock(status_code=200)
        mocked_get.return_value.raise_for_status = Mock()
        mocked_get.return_value.json.return_value = {
            'id': '5555',
            'username': 'coach_raven',
            'global_name': 'Coach Raven',
            'avatar': 'hash5555',
        }
        self.client.login(username='coach', password='secret-pass')
        connect_response = self.client.get(reverse('api_discord_connect'))
        self.assertEqual(connect_response.status_code, 302)
        state = self.client.session['discord_oauth_state']

        response = self.client.get(reverse('api_discord_callback'), {'code': 'oauth-code', 'state': state})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/profile/?discord=connected')
        connection = DiscordConnection.objects.get(user=staff_user)
        self.assertEqual(connection.username, 'coach_raven')
        staff_member.refresh_from_db()
        self.assertEqual(staff_member.user_id, staff_user.id)

    def test_callback_rejects_invalid_state(self):
        self.client.login(username='avatar-user', password='secret-pass')

        response = self.client.get(reverse('api_discord_callback'), {'code': 'oauth-code', 'state': 'wrong'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/profile/?discord=error&reason=invalid-state')

    @patch('scheduler.api.requests.get')
    @patch('scheduler.api.requests.post')
    def test_callback_rejects_already_linked_discord_user(self, mocked_post, mocked_get):
        other_user = User.objects.create_user(username='other-user', password='secret-pass')
        DiscordConnection.objects.create(
            user=other_user,
            discord_user_id='7777',
            username='taken_handle',
            global_name='Taken Handle',
            avatar_hash='hash7777',
        )
        mocked_post.return_value = Mock(status_code=200)
        mocked_post.return_value.raise_for_status = Mock()
        mocked_post.return_value.json.return_value = {'access_token': 'discord-token'}
        mocked_get.return_value = Mock(status_code=200)
        mocked_get.return_value.raise_for_status = Mock()
        mocked_get.return_value.json.return_value = {
            'id': '7777',
            'username': 'taken_handle',
            'global_name': 'Taken Handle',
            'avatar': 'hash7777',
        }
        self.client.login(username='avatar-user', password='secret-pass')
        self.client.get(reverse('api_discord_connect'))
        state = self.client.session['discord_oauth_state']

        response = self.client.get(reverse('api_discord_callback'), {'code': 'oauth-code', 'state': state})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/profile/?discord=error&reason=already-linked')
        self.assertFalse(DiscordConnection.objects.filter(user=self.user, discord_user_id='7777').exists())

    @patch('scheduler.api.requests.get')
    @patch('scheduler.api.requests.post')
    def test_callback_reconnect_updates_existing_connection(self, mocked_post, mocked_get):
        DiscordConnection.objects.create(
            user=self.user,
            discord_user_id='8888',
            username='old_handle',
            global_name='Old Name',
            avatar_hash='oldhash',
        )
        mocked_post.return_value = Mock(status_code=200)
        mocked_post.return_value.raise_for_status = Mock()
        mocked_post.return_value.json.return_value = {'access_token': 'discord-token'}
        mocked_get.return_value = Mock(status_code=200)
        mocked_get.return_value.raise_for_status = Mock()
        mocked_get.return_value.json.return_value = {
            'id': '8888',
            'username': 'new_handle',
            'global_name': 'New Name',
            'avatar': 'newhash',
        }
        self.client.login(username='avatar-user', password='secret-pass')
        self.client.get(reverse('api_discord_connect'))
        state = self.client.session['discord_oauth_state']

        response = self.client.get(reverse('api_discord_callback'), {'code': 'oauth-code', 'state': state})

        self.assertEqual(response.status_code, 302)
        connection = DiscordConnection.objects.get(user=self.user)
        self.assertEqual(connection.username, 'new_handle')
        self.assertEqual(connection.global_name, 'New Name')
        self.assertEqual(connection.avatar_hash, 'newhash')

    def test_disconnect_removes_only_current_user_connection(self):
        other_user = User.objects.create_user(username='other-user', password='secret-pass')
        DiscordConnection.objects.create(
            user=self.user,
            discord_user_id='9999',
            username='avatar-user',
            global_name='Avatar User',
            avatar_hash='hash9999',
        )
        DiscordConnection.objects.create(
            user=other_user,
            discord_user_id='10000',
            username='other-user',
            global_name='Other User',
            avatar_hash='hash10000',
        )
        self.client.login(username='avatar-user', password='secret-pass')

        response = self.client.post(reverse('api_discord_disconnect'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DiscordConnection.objects.filter(user=self.user).exists())
        self.assertTrue(DiscordConnection.objects.filter(user=other_user).exists())


class RosterResetTests(TestCase):
    def setUp(self):
        self.player = Player.objects.get(name='Игрок 1')
        self.user = User.objects.create_superuser(username='admin', email='admin@example.com', password='secret-pass')

    def test_auto_reset_clears_only_slots_on_new_week(self):
        original_player_count = Player.objects.count()
        ScheduleSlot.objects.create(
            player=self.player,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        RosterState.objects.create(pk=1, current_week_start=date(2026, 4, 20))

        changed, deleted_count = ensure_current_roster_week(today=date(2026, 4, 27))

        self.assertTrue(changed)
        self.assertGreaterEqual(deleted_count, 1)
        self.assertEqual(ScheduleSlot.objects.count(), 0)
        self.assertEqual(Player.objects.count(), original_player_count)
        self.assertEqual(StaffMember.objects.count(), 0)
        self.assertEqual(str(RosterState.objects.get(pk=1).current_week_start), '2026-04-27')

    def test_admin_reset_button_clears_schedule(self):
        ScheduleSlot.objects.create(
            player=self.player,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='admin', password='secret-pass')

        response = self.client.post(reverse('admin:scheduler_scheduleslot_reset_table'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(ScheduleSlot.objects.count(), 0)


class AdminConfigurationTests(TestCase):
    def test_player_admin_hides_legacy_avatar_and_discord_fields(self):
        admin_instance = PlayerAdmin(Player, admin.site)

        self.assertNotIn('avatar_upload', admin_instance.fields)
        self.assertNotIn('avatar_link', admin_instance.fields)
        self.assertNotIn('discord_tag', admin_instance.fields)
        self.assertIn('discord_status', admin_instance.fields)
        self.assertIn('discord_avatar_preview', admin_instance.fields)

    def test_staff_admin_hides_legacy_discord_field(self):
        admin_instance = StaffMemberAdmin(StaffMember, admin.site)

        self.assertNotIn('discord_tag', admin_instance.fields)
        self.assertIn('discord_status', admin_instance.fields)
        self.assertIn('discord_avatar_preview', admin_instance.fields)

    def test_player_inline_hides_legacy_avatar_and_discord_fields(self):
        self.assertNotIn('avatar_upload', PlayerInline.fields)
        self.assertNotIn('avatar_link', PlayerInline.fields)
        self.assertNotIn('discord_tag', PlayerInline.fields)
        self.assertIn('discord_status', PlayerInline.fields)

# Create your tests here.
