from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from .forms import ScheduleSlotForm
from .models import DayEventType, DiscordConnection, Player, RosterState, ScheduleSlot, StaffMember, default_week_start
from .roster import ensure_current_roster_week


class ScheduleFormTests(TestCase):
    def test_allows_end_time_2400(self):
        DayEventType.objects.update_or_create(
            week_start=default_week_start(),
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
            week_start=default_week_start(),
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


class ScheduleSlotModelTests(TestCase):
    def setUp(self):
        self.player = Player.objects.get(name='Игрок 1')

    def test_available_slot_requires_start_and_end_time(self):
        slot = ScheduleSlot(
            player=self.player,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
        )

        with self.assertRaises(ValidationError) as context:
            slot.full_clean()

        self.assertIn('start_time_minutes', context.exception.error_dict)
        self.assertIn('end_time_minutes', context.exception.error_dict)

    def test_available_slot_requires_end_after_start(self):
        slot = ScheduleSlot(
            player=self.player,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=900,
            end_time_minutes=900,
        )

        with self.assertRaises(ValidationError) as context:
            slot.full_clean()

        self.assertIn('end_time_minutes', context.exception.error_dict)

    def test_available_slot_rejects_time_outside_day_range(self):
        slot = ScheduleSlot(
            player=self.player,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=900,
            end_time_minutes=1500,
        )

        with self.assertRaises(ValidationError) as context:
            slot.full_clean()

        self.assertIn('end_time_minutes', context.exception.error_dict)

    def test_all_day_status_clears_time_fields(self):
        slot = ScheduleSlot(
            player=self.player,
            slot_type=ScheduleSlot.UNAVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=900,
            end_time_minutes=1200,
        )

        slot.full_clean()

        self.assertIsNone(slot.start_time_minutes)
        self.assertIsNone(slot.end_time_minutes)


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

    def test_hidden_main_page_requires_login(self):
        response = self.client.get(reverse('main'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_hidden_main_page_renders_spa_for_logged_in_user(self):
        self.client.login(username='player1', password='secret-pass')

        response = self.client.get(reverse('main'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'root')

    def test_login_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse('login'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<span>Your</span>', html=True)
        self.assertContains(response, 'data-clock="local"')
        self.assertContains(response, 'data-password-toggle')
        self.assertContains(response, 'aria-label="Показать пароль"')

    def test_schedule_shows_player_role(self):
        self.player_one.role = 'Leader'
        self.player_one.save()
        self.client.login(username='player1', password='secret-pass')
        response = self.client.get(reverse('api_bootstrap'))
        self.assertContains(response, 'Leader')

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

    def test_legacy_slot_html_routes_are_removed(self):
        self.client.login(username='player1', password='secret-pass')

        self.assertEqual(self.client.get('/slot/new/').status_code, 404)
        self.assertEqual(self.client.get('/slot/1/edit/').status_code, 404)
        self.assertEqual(self.client.get('/slot/1/delete/').status_code, 404)


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
            week_start=default_week_start(),
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
        self.assertIn('selectedWeekStart', data)
        self.assertIn('currentWeekStart', data)
        self.assertIn('weekRangeLabel', data)
        self.assertTrue(data['canEditSelectedWeek'])
        self.assertIn('earliestFilledWeekStart', data)
        self.assertIn('canGoPreviousWeek', data)
        self.assertIn('copySourceWeeks', data)
        self.assertIn('copyTargetWeeks', data)

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

    def test_bootstrap_filters_slots_by_selected_week(self):
        current_week = date(2026, 4, 27)
        previous_week = date(2026, 4, 20)
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': current_week})
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=previous_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
            note='old week',
        )
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=current_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=720,
            end_time_minutes=840,
            note='current week',
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.client.get(reverse('api_bootstrap'), {'week': '2026-04-22'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['selectedWeekStart'], '2026-04-20')
        self.assertEqual(data['currentWeekStart'], '2026-04-27')
        self.assertEqual(data['weekRangeLabel'], '20 Апреля - 26 Апреля')
        self.assertFalse(data['canEditSelectedWeek'])
        self.assertEqual([slot['note'] for slot in data['slots']], ['old week'])
        self.assertEqual(data['days'][0]['date'], '20.04')
        self.assertEqual(data['earliestFilledWeekStart'], '2026-04-20')
        self.assertFalse(data['canGoPreviousWeek'])

    def test_bootstrap_clamps_week_before_earliest_team_slot(self):
        current_week = date(2026, 4, 27)
        earliest_week = date(2026, 4, 20)
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': current_week})
        ScheduleSlot.objects.create(
            player=self.player_two,
            week_start=earliest_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
            note='team earliest',
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.client.get(reverse('api_bootstrap'), {'week': '2026-04-13'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['selectedWeekStart'], '2026-04-20')
        self.assertEqual(data['earliestFilledWeekStart'], '2026-04-20')
        self.assertFalse(data['canGoPreviousWeek'])
        self.assertEqual([slot['note'] for slot in data['slots']], ['team earliest'])

    def test_bootstrap_keeps_current_week_when_only_future_slots_exist(self):
        current_week = date(2026, 4, 27)
        future_week = date(2026, 5, 4)
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': current_week})
        ScheduleSlot.objects.create(
            player=self.player_two,
            week_start=future_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
            note='future only',
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['selectedWeekStart'], '2026-04-27')
        self.assertEqual(data['earliestFilledWeekStart'], '2026-04-27')
        self.assertFalse(data['canGoPreviousWeek'])

    def test_bootstrap_filters_day_event_types_by_selected_week(self):
        current_week = date(2026, 4, 27)
        previous_week = date(2026, 4, 20)
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': current_week})
        DayEventType.objects.create(
            week_start=previous_week,
            day_of_week=ScheduleSlot.MONDAY,
            event_type=ScheduleSlot.SCRIM,
        )
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=previous_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
            note='old week',
        )
        DayEventType.objects.update_or_create(
            week_start=current_week,
            day_of_week=ScheduleSlot.MONDAY,
            defaults={'event_type': ScheduleSlot.TOURNAMENT},
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.client.get(reverse('api_bootstrap'), {'week': '2026-04-22'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['dayEventTypes']), 1)
        self.assertEqual(data['dayEventTypes'][0]['weekStart'], '2026-04-20')
        self.assertEqual(data['dayEventTypes'][0]['eventType'], ScheduleSlot.SCRIM)

    def test_bootstrap_returns_copy_week_options_for_current_player(self):
        current_week = date(2026, 4, 27)
        next_week = date(2026, 5, 4)
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': current_week})
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=current_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
            note='source one',
        )
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=current_week,
            slot_type=ScheduleSlot.TENTATIVE,
            day_of_week=ScheduleSlot.TUESDAY,
            note='source two',
        )
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=next_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.WEDNESDAY,
            start_time_minutes=720,
            end_time_minutes=840,
        )
        ScheduleSlot.objects.create(
            player=self.player_two,
            week_start=date(2026, 4, 20),
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.client.get(reverse('api_bootstrap'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['earliestFilledWeekStart'], '2026-04-20')
        self.assertEqual(
            [(week['weekStart'], week['slotCount']) for week in data['copySourceWeeks']],
            [('2026-05-04', 1), ('2026-04-27', 2)],
        )
        self.assertEqual(data['copyTargetWeeks'][0]['weekStart'], '2026-04-27')
        self.assertEqual(data['copyTargetWeeks'][-1]['weekStart'], '2026-07-20')

    def test_bootstrap_rejects_invalid_week_query(self):
        self.client.login(username='player1', password='secret-pass')

        response = self.client.get(reverse('api_bootstrap'), {'week': 'bad-week'})

        self.assertEqual(response.status_code, 400)

    def test_api_creates_event_using_day_type(self):
        DayEventType.objects.update_or_create(
            week_start=default_week_start(),
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
        self.assertEqual(response.json()['slot']['weekStart'], slot.week_start.isoformat())
        self.assertEqual(response.json()['slot']['eventType'], ScheduleSlot.TOURNAMENT)
        self.assertEqual(response.json()['slot']['eventLabel'], 'Tournament')

    def test_api_creates_slot_for_future_week(self):
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': date(2026, 4, 27)})
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.post_json('api_slot_create', {
                'weekStart': '2026-05-06',
                'slotType': ScheduleSlot.AVAILABLE,
                'dayOfWeek': ScheduleSlot.SATURDAY,
                'startTimeMinutes': 1200,
                'endTimeMinutes': 1380,
                'note': 'future',
            })

        self.assertEqual(response.status_code, 201)
        slot = ScheduleSlot.objects.get(player=self.player_one, note='future')
        self.assertEqual(str(slot.week_start), '2026-05-04')
        self.assertEqual(response.json()['slot']['weekStart'], '2026-05-04')

    def test_api_rejects_create_for_past_week(self):
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': date(2026, 4, 27)})
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.post_json('api_slot_create', {
                'weekStart': '2026-04-20',
                'slotType': ScheduleSlot.AVAILABLE,
                'dayOfWeek': ScheduleSlot.SATURDAY,
                'startTimeMinutes': 1200,
                'endTimeMinutes': 1380,
                'note': '',
            })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ScheduleSlot.objects.filter(week_start=date(2026, 4, 20)).exists())

    def test_api_copies_own_week_and_replaces_target_slots(self):
        current_week = date(2026, 4, 27)
        source_week = date(2026, 4, 20)
        target_week = date(2026, 5, 4)
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': current_week})
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=source_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
            note='copy me',
        )
        ScheduleSlot.objects.create(
            player=self.player_two,
            week_start=source_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.TUESDAY,
            start_time_minutes=720,
            end_time_minutes=840,
            note='do not copy',
        )
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=target_week,
            slot_type=ScheduleSlot.TENTATIVE,
            day_of_week=ScheduleSlot.WEDNESDAY,
            note='replace me',
        )
        ScheduleSlot.objects.create(
            player=self.player_two,
            week_start=target_week,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.THURSDAY,
            start_time_minutes=840,
            end_time_minutes=960,
            note='keep other player',
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.post_json('api_slot_copy_week', {
                'sourceWeekStart': '2026-04-20',
                'targetWeekStart': '2026-05-04',
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['copiedCount'], 1)
        copied_slots = list(ScheduleSlot.objects.filter(player=self.player_one, week_start=target_week))
        self.assertEqual(len(copied_slots), 1)
        self.assertEqual(copied_slots[0].note, 'copy me')
        self.assertEqual(copied_slots[0].day_of_week, ScheduleSlot.MONDAY)
        self.assertTrue(ScheduleSlot.objects.filter(player=self.player_two, week_start=target_week, note='keep other player').exists())
        self.assertFalse(ScheduleSlot.objects.filter(player=self.player_one, week_start=target_week, note='replace me').exists())

    def test_api_copy_week_rejects_past_target(self):
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': date(2026, 4, 27)})
        ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=date(2026, 4, 27),
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.post_json('api_slot_copy_week', {
                'sourceWeekStart': '2026-04-27',
                'targetWeekStart': '2026-04-20',
            })

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ScheduleSlot.objects.filter(week_start=date(2026, 4, 20)).exists())

    def test_api_copy_week_rejects_same_week(self):
        self.client.login(username='player1', password='secret-pass')

        response = self.post_json('api_slot_copy_week', {
            'sourceWeekStart': '2026-04-27',
            'targetWeekStart': '2026-04-27',
        })

        self.assertEqual(response.status_code, 400)

    def test_api_copy_week_rejects_source_without_own_slots(self):
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': date(2026, 4, 27)})
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.post_json('api_slot_copy_week', {
                'sourceWeekStart': '2026-04-20',
                'targetWeekStart': '2026-04-27',
            })

        self.assertEqual(response.status_code, 400)

    def test_api_copy_week_requires_player_profile(self):
        user = User.objects.create_user(username='viewer', password='secret-pass')
        self.client.login(username='viewer', password='secret-pass')

        response = self.post_json('api_slot_copy_week', {
            'sourceWeekStart': '2026-04-20',
            'targetWeekStart': '2026-04-27',
        })

        self.assertEqual(response.status_code, 403)

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

    def test_api_updates_own_slot(self):
        slot = ScheduleSlot.objects.create(
            player=self.player_one,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')

        response = self.patch_json('api_slot_update', {
            'slotType': ScheduleSlot.AVAILABLE,
            'dayOfWeek': ScheduleSlot.WEDNESDAY,
            'startTimeMinutes': 900,
            'endTimeMinutes': 1020,
            'note': 'Новый слот',
        }, args=[slot.pk])

        self.assertEqual(response.status_code, 200)
        slot.refresh_from_db()
        self.assertEqual(slot.day_of_week, ScheduleSlot.WEDNESDAY)
        self.assertEqual(slot.start_time_minutes, 900)
        self.assertEqual(slot.end_time_minutes, 1020)
        self.assertEqual(slot.note, 'Новый слот')

    def test_api_rejects_update_for_past_week(self):
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': date(2026, 4, 27)})
        slot = ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=date(2026, 4, 20),
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.patch_json('api_slot_update', {
                'slotType': ScheduleSlot.AVAILABLE,
                'dayOfWeek': ScheduleSlot.WEDNESDAY,
                'startTimeMinutes': 900,
                'endTimeMinutes': 1020,
                'note': 'archive edit',
            }, args=[slot.pk])

        self.assertEqual(response.status_code, 403)
        slot.refresh_from_db()
        self.assertEqual(slot.day_of_week, ScheduleSlot.MONDAY)
        self.assertEqual(slot.note, '')

    def test_api_deletes_own_slot(self):
        slot = ScheduleSlot.objects.create(
            player=self.player_one,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')

        response = self.client.delete(reverse('api_slot_delete', args=[slot.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(ScheduleSlot.objects.filter(pk=slot.pk).exists())

    def test_api_rejects_delete_for_past_week(self):
        RosterState.objects.update_or_create(pk=1, defaults={'current_week_start': date(2026, 4, 27)})
        slot = ScheduleSlot.objects.create(
            player=self.player_one,
            week_start=date(2026, 4, 20),
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='player1', password='secret-pass')

        with patch('scheduler.roster.timezone.localdate', return_value=date(2026, 4, 30)):
            response = self.client.delete(reverse('api_slot_delete', args=[slot.pk]))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(ScheduleSlot.objects.filter(pk=slot.pk).exists())

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


class RosterResetTests(TestCase):
    def setUp(self):
        self.player = Player.objects.get(name='Игрок 1')
        self.user = User.objects.create_superuser(username='admin', email='admin@example.com', password='secret-pass')

    def test_auto_week_advance_keeps_historical_slots(self):
        original_player_count = Player.objects.count()
        ScheduleSlot.objects.create(
            player=self.player,
            week_start=date(2026, 4, 20),
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        RosterState.objects.create(pk=1, current_week_start=date(2026, 4, 20))

        changed, deleted_count = ensure_current_roster_week(today=date(2026, 4, 27))

        self.assertTrue(changed)
        self.assertEqual(deleted_count, 0)
        self.assertEqual(ScheduleSlot.objects.count(), 1)
        self.assertEqual(Player.objects.count(), original_player_count)
        self.assertEqual(StaffMember.objects.count(), 0)
        self.assertEqual(str(RosterState.objects.get(pk=1).current_week_start), '2026-04-27')

    def test_admin_reset_button_is_removed(self):
        ScheduleSlot.objects.create(
            player=self.player,
            slot_type=ScheduleSlot.AVAILABLE,
            day_of_week=ScheduleSlot.MONDAY,
            start_time_minutes=600,
            end_time_minutes=720,
        )
        self.client.login(username='admin', password='secret-pass')

        with self.assertRaises(NoReverseMatch):
            reverse('admin:scheduler_scheduleslot_reset_table')
        self.assertEqual(ScheduleSlot.objects.count(), 1)
