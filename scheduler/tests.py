from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import ScheduleSlotForm
from .models import DayEventType, Player, ScheduleSlot


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
            defaults={'event_type': ScheduleSlot.PRACTICE},
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

    def test_rejects_available_without_day_event_type(self):
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.AVAILABLE,
            'day_of_week': ScheduleSlot.TUESDAY,
            'start_time_minutes': 1080,
            'end_time_minutes': 1200,
            'note': '',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('day_of_week', form.errors)

    def test_allows_unavailable_without_time(self):
        form = ScheduleSlotForm(data={
            'slot_type': ScheduleSlot.UNAVAILABLE,
            'day_of_week': ScheduleSlot.FRIDAY,
            'note': 'Не смогу играть',
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
        self.client.login(username='player1', password='secret-pass')
        response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user']['username'], 'player1')
        self.assertTrue(any(player['role'] == 'Leader' for player in data['players']))
        self.assertTrue(any(event_type['value'] == ScheduleSlot.SCRIM for event_type in data['eventTypes']))
        self.assertTrue(any(day_event['eventType'] == ScheduleSlot.SCRIM for day_event in data['dayEventTypes']))

    def test_api_creates_event_using_day_type(self):
        DayEventType.objects.update_or_create(
            day_of_week=ScheduleSlot.SATURDAY,
            defaults={'event_type': ScheduleSlot.MATCH},
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
        self.assertEqual(response.json()['slot']['eventType'], ScheduleSlot.MATCH)
        self.assertEqual(response.json()['slot']['eventLabel'], 'Матч')

    def test_api_rejects_available_without_day_event_type(self):
        self.client.login(username='player1', password='secret-pass')
        response = self.post_json('api_slot_create', {
            'slotType': ScheduleSlot.AVAILABLE,
            'dayOfWeek': ScheduleSlot.SATURDAY,
            'startTimeMinutes': 1200,
            'endTimeMinutes': 1380,
            'note': '',
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('day_of_week', response.json()['errors'])

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

# Create your tests here.
