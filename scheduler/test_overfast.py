from unittest.mock import call, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import OverwatchStatsCache, Player
from .overfast import (
    OverfastError,
    build_overwatch_stats_dashboard,
    normalize_battle_tag,
    primary_battle_tag,
    rank_label_from_score,
    rank_rating_from_score,
    rank_score,
    refresh_overwatch_stats,
)


OVERFAST_SUMMARY_SAMPLE = {
    'competitive': {
        'pc': {
            'season': 22,
            'tank': {
                'division': 'diamond',
                'tier': 2,
                'rank_icon': 'https://example.com/diamond-2.png',
                'role_icon': 'https://example.com/tank.png',
            },
            'damage': None,
            'support': None,
            'open': None,
        },
    },
}

OVERFAST_STATS_SAMPLE = {
    'general': {
        'games_played': 10,
        'games_won': 6,
        'games_lost': 4,
        'time_played': 7200,
        'winrate': 60.0,
        'total': {
            'eliminations': 120,
            'deaths': 60,
            'damage': 100000,
        },
        'average': {
            'damage': 10000,
            'eliminations': 12,
            'deaths': 6,
        },
    },
    'heroes': {
        'cassidy': {
            'games_played': 5,
            'games_won': 3,
            'games_lost': 2,
            'time_played': 3600,
            'average': {'damage': 9000},
        },
        'ana': {
            'games_played': 3,
            'games_won': 2,
            'games_lost': 1,
            'time_played': 1800,
            'average': {'damage': 4200},
        },
    },
}


class OverwatchStatsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='stats-user', password='secret-pass')
        self.player = Player.objects.get(name='Игрок 1')
        self.player.name = 'Forin'
        self.player.role = 'Tank'
        self.player.battle_tags = 'Forin#21436\nForinAlt#1111'
        self.player.user = self.user
        self.player.save()

    def test_normalizes_battle_tag_and_uses_first_player_tag(self):
        self.assertEqual(normalize_battle_tag('Forin#21436'), 'Forin-21436')
        self.assertEqual(primary_battle_tag(self.player), 'Forin#21436')

    def test_accepts_overfast_ultimate_rank_as_champion(self):
        rank = {'division': 'ultimate', 'tier': 1}

        score = rank_score(rank)

        self.assertEqual(rank_label_from_score(score), 'Champion 1')
        self.assertEqual(rank_rating_from_score(score), 5000)

    @patch('scheduler.overfast_sync.fetch_overfast_stats')
    @patch('scheduler.overfast_sync.fetch_overfast_summary')
    def test_refresh_creates_competitive_cache(self, mocked_summary, mocked_stats):
        mocked_summary.return_value = OVERFAST_SUMMARY_SAMPLE
        mocked_stats.return_value = OVERFAST_STATS_SAMPLE

        result = refresh_overwatch_stats([self.player])

        self.assertEqual(result['updated'], 1)
        mocked_summary.assert_called_once_with('Forin-21436')
        mocked_stats.assert_has_calls([
            call('Forin-21436', OverwatchStatsCache.COMPETITIVE),
        ])
        caches = OverwatchStatsCache.objects.filter(player=self.player).order_by('mode')
        self.assertEqual(caches.count(), 1)
        self.assertTrue(all(cache.status == OverwatchStatsCache.STATUS_READY for cache in caches))
        self.assertTrue(all(cache.overfast_player_id == 'Forin-21436' for cache in caches))

    @patch('scheduler.overfast_sync.fetch_overfast_summary')
    def test_refresh_saves_api_error_per_mode(self, mocked_summary):
        mocked_summary.side_effect = OverfastError('Профиль не найден или закрыт.')

        result = refresh_overwatch_stats([self.player])

        self.assertEqual(result['errors'], 1)
        caches = OverwatchStatsCache.objects.filter(player=self.player)
        self.assertEqual(caches.count(), 1)
        self.assertTrue(all(cache.status == OverwatchStatsCache.STATUS_ERROR for cache in caches))
        self.assertTrue(all(cache.error == 'Профиль не найден или закрыт.' for cache in caches))

    def test_dashboard_aggregates_cached_metrics(self):
        OverwatchStatsCache.objects.create(
            player=self.player,
            battle_tag='Forin#21436',
            overfast_player_id='Forin-21436',
            mode=OverwatchStatsCache.COMPETITIVE,
            status=OverwatchStatsCache.STATUS_READY,
            summary_json=OVERFAST_SUMMARY_SAMPLE,
            stats_json=OVERFAST_STATS_SAMPLE,
        )

        dashboard = build_overwatch_stats_dashboard(
            OverwatchStatsCache.COMPETITIVE,
            {'cassidy': 'https://example.com/cassidy.png', 'ana': 'https://example.com/ana.png'},
        )

        player_row = next(row for row in dashboard['players'] if row['id'] == self.player.id)
        self.assertEqual(player_row['rank']['label'], 'Diamond 2')
        self.assertNotIn('sr', player_row)
        self.assertEqual(player_row['winrate'], 60.0)
        self.assertEqual(player_row['matches'], 10)
        self.assertEqual(player_row['wins'], 6)
        self.assertEqual(player_row['losses'], 4)
        self.assertEqual(player_row['kd'], 2.0)
        self.assertEqual(player_row['avgEliminations'], 12)
        self.assertEqual(player_row['mainHero']['hero'], 'cassidy')
        self.assertEqual(player_row['mainHero']['heroIconUrl'], 'https://example.com/cassidy.png')
        self.assertNotIn('recentGamesAvailable', player_row)
        self.assertEqual(dashboard['team']['winrate'], 60.0)
        self.assertEqual(dashboard['team']['matches'], 10)
        self.assertEqual(dashboard['team']['averageRank'], 'Diamond 2')
        self.assertEqual(dashboard['team']['averageRating'], 3300)
        self.assertNotIn('bestStreak', dashboard['team'])
        self.assertNotIn('worstStreak', dashboard['team'])
        self.assertEqual(dashboard['topHeroes'][0]['hero'], 'cassidy')
        self.assertEqual(dashboard['topHeroes'][0]['heroIconUrl'], 'https://example.com/cassidy.png')
        self.assertEqual(dashboard['topHeroes'][0]['timePlayed'], 3600)
        self.assertNotIn('unavailableMessage', dashboard)

    def test_dashboard_serializes_overfast_ultimate_rank(self):
        summary = {
            'competitive': {
                'pc': {
                    'season': 22,
                    'tank': {
                        'division': 'ultimate',
                        'tier': 1,
                        'rank_icon': 'https://example.com/champion-1.png',
                        'role_icon': 'https://example.com/tank.png',
                    },
                    'damage': None,
                    'support': None,
                    'open': None,
                },
            },
        }
        OverwatchStatsCache.objects.create(
            player=self.player,
            battle_tag='Forin#21436',
            overfast_player_id='Forin-21436',
            mode=OverwatchStatsCache.COMPETITIVE,
            status=OverwatchStatsCache.STATUS_READY,
            summary_json=summary,
            stats_json=OVERFAST_STATS_SAMPLE,
        )

        dashboard = build_overwatch_stats_dashboard(OverwatchStatsCache.COMPETITIVE)

        player_row = next(row for row in dashboard['players'] if row['id'] == self.player.id)
        self.assertEqual(player_row['rank']['division'], 'ultimate')
        self.assertEqual(player_row['rank']['label'], 'Champion 1')
        self.assertEqual(player_row['rank']['rating'], 5000)
        self.assertEqual(dashboard['team']['averageRank'], 'Champion 1')
        self.assertEqual(dashboard['team']['averageRating'], 5000)

    @patch('scheduler.api_stats.get_hero_portrait_map')
    def test_stats_api_returns_dashboard(self, mocked_hero_portraits):
        mocked_hero_portraits.return_value = {'cassidy': 'https://example.com/cassidy.png'}
        OverwatchStatsCache.objects.create(
            player=self.player,
            battle_tag='Forin#21436',
            overfast_player_id='Forin-21436',
            mode=OverwatchStatsCache.COMPETITIVE,
            status=OverwatchStatsCache.STATUS_READY,
            summary_json=OVERFAST_SUMMARY_SAMPLE,
            stats_json=OVERFAST_STATS_SAMPLE,
        )
        self.client.login(username='stats-user', password='secret-pass')

        response = self.client.get(reverse('api_overwatch_stats'), {'mode': OverwatchStatsCache.COMPETITIVE})

        self.assertEqual(response.status_code, 200)
        payload = response.json()['stats']
        self.assertEqual(payload['mode'], OverwatchStatsCache.COMPETITIVE)
        self.assertEqual(payload['team']['matches'], 10)
        self.assertEqual(payload['topHeroes'][0]['heroIconUrl'], 'https://example.com/cassidy.png')
