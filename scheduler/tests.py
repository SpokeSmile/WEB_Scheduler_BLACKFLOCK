from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .admin import PlayerAdminForm
from .forms import ScheduleSlotForm
from .models import DayEventType, Player, ScheduleSlot, StaffMember


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
        self.player_one.discord_tag = 'blackflock_main'
        self.player_one.role_color = '#123456'
        self.player_one.save()
        StaffMember.objects.create(
            name='Coach Raven',
            role='Coach',
            role_color='#f3701e',
            discord_tag='coach_raven',
            sort_order=1,
        )
        self.client.login(username='player1', password='secret-pass')
        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user']['username'], 'player1')
        self.assertTrue(any(player['role'] == 'Leader' for player in data['players']))
        self.assertTrue(any(player['roleColor'] == '#123456' for player in data['players']))
        self.assertTrue(any(player['discordTag'] == 'blackflock_main' for player in data['players']))
        self.assertTrue(any(player['battleTags'] == ['BlackFlock#1111', 'AltBird#2222'] for player in data['players']))
        self.assertTrue(any(staff_member['role'] == 'Coach' for staff_member in data['staffMembers']))
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
            'battleTagsText': 'BlackFlock#1111\nAltBird#2222',
            'discordTag': 'blackflock_main',
        })

        self.assertEqual(response.status_code, 200)
        self.player_one.refresh_from_db()
        self.assertEqual(self.player_one.battle_tags_list, ['BlackFlock#1111', 'AltBird#2222'])
        self.assertEqual(self.player_one.discord_tag, 'blackflock_main')
        self.assertEqual(response.json()['player']['discordTag'], 'blackflock_main')


class PlayerAvatarTests(TestCase):
    def test_resolved_avatar_url_prefers_embedded_avatar(self):
        player = Player.objects.create(
            name='Игрок с аватаром',
            avatar_data=b'avatar-binary',
            avatar_content_type='image/png',
            avatar_link='https://example.com/fallback.png',
        )

        self.assertTrue(player.resolved_avatar_url.startswith('data:image/png;base64,'))

    def test_admin_form_saves_uploaded_avatar_to_database(self):
        avatar_upload = SimpleUploadedFile(
            'avatar.png',
            b'avatar-binary',
            content_type='image/png',
        )
        form = PlayerAdminForm(
            data={
                'name': 'Игрок формы',
                'role': '',
                'role_color': '#4b607f',
                'sort_order': 0,
                'avatar_link': '',
                'battle_tags': '',
                'discord_tag': '',
                'remove_uploaded_avatar': '',
            },
            files={'avatar_upload': avatar_upload},
        )

        self.assertTrue(form.is_valid(), form.errors)
        player = form.save()
        self.assertEqual(player.avatar_content_type, 'image/png')
        self.assertEqual(bytes(player.avatar_data), b'avatar-binary')

    def test_bootstrap_returns_embedded_avatar(self):
        player = Player.objects.get(name='Игрок 1')
        user = User.objects.create_user(username='avatar-user', password='secret-pass')
        player.user = user
        player.avatar_data = b'avatar-binary'
        player.avatar_content_type = 'image/png'
        player.save()
        self.client.login(username='avatar-user', password='secret-pass')

        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        avatar_url = next(item['avatarUrl'] for item in response.json()['players'] if item['id'] == player.id)
        self.assertTrue(avatar_url.startswith('data:image/png;base64,'))

# Create your tests here.
