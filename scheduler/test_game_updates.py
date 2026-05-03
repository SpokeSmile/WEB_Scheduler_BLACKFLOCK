from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .game_updates import extract_archive_months, parse_game_updates_html, sync_game_updates
from .models import GameUpdate


PATCH_NOTES_SAMPLE_HTML = """
<div class="PatchNotes-patch PatchNotes-live">
  <div class="anchor" id="patch-2026-04-23"></div>
  <div class="PatchNotes-labels"><div class="PatchNotes-date">April 23, 2026</div></div>
  <h3 class="PatchNotes-patchTitle">Overwatch Retail Patch Notes – April 23, 2026</h3>
  <div class="PatchNotes-section PatchNotes-section-generic_update">
    <h4 class="PatchNotes-sectionTitle">Balance Hotfix Update</h4>
    <div class="PatchNotes-sectionDescription"><p>This is a balance hotfix update.</p></div>
  </div>
  <div class="PatchNotesHeroUpdate">
    <div class="PatchNotesHeroUpdate-header">
      <img class="PatchNotesHeroUpdate-icon" src="https://example.com/roadhog.png" alt="Roadhog">
      <h5 class="PatchNotesHeroUpdate-name">Roadhog</h5>
    </div>
    <div class="PatchNotesHeroUpdate-body">
      <div class="PatchNotesHeroUpdate-abilitiesList">
        <div class="PatchNotesAbilityUpdate">
          <div class="PatchNotesAbilityUpdate-text">
            <div class="PatchNotesAbilityUpdate-name">Chain Hook</div>
            <div class="PatchNotesAbilityUpdate-detailList">
              <ul>
                <li>Cooldown reduced from 8 to 7 seconds.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="PatchNotesTop">Top of post</div>
</div>
<div class="PatchNotes-patch PatchNotes-live">
  <div class="anchor" id="patch-2026-04-18"></div>
  <div class="PatchNotes-labels"><div class="PatchNotes-date">April 18, 2026</div></div>
  <h3 class="PatchNotes-patchTitle">Overwatch Retail Patch Notes – April 18, 2026</h3>
  <div class="PatchNotes-section PatchNotes-section-generic_update">
    <h4 class="PatchNotes-sectionTitle">Bug Fix Update</h4>
    <div class="PatchNotes-sectionDescription"><p>This is a bug fix update.</p></div>
  </div>
  <div class="PatchNotesGeneralUpdate">
    <div class="PatchNotesGeneralUpdate-title">General</div>
    <div class="PatchNotesGeneralUpdate-description">
      <ul>
        <li>Fixed a bug in matchmaking.</li>
      </ul>
    </div>
  </div>
</div>
"""

PATCH_NOTES_ROOT_HTML = """
<script>
patchNotesDates = {"live":["2026-04","2026-03","2026-02"]};
</script>
""" + PATCH_NOTES_SAMPLE_HTML

PATCH_NOTES_ARCHIVE_MARCH_HTML = """
<div class="PatchNotes-patch PatchNotes-live">
  <div class="anchor" id="patch-2026-03-31"></div>
  <div class="PatchNotes-labels"><div class="PatchNotes-date">March 31, 2026</div></div>
  <h3 class="PatchNotes-patchTitle">Overwatch Retail Patch Notes - March 31, 2026</h3>
  <div class="PatchNotes-section PatchNotes-section-generic_update">
    <h4 class="PatchNotes-sectionTitle">Season Update</h4>
    <div class="PatchNotes-sectionDescription"><p>This is a seasonal patch update.</p></div>
  </div>
</div>
"""

PATCH_NOTES_ARCHIVE_FEB_HTML = """
<div class="PatchNotes-patch PatchNotes-live">
  <div class="anchor" id="patch-2026-02-25"></div>
  <div class="PatchNotes-labels"><div class="PatchNotes-date">February 25, 2026</div></div>
  <h3 class="PatchNotes-patchTitle">Overwatch Retail Patch Notes - February 25, 2026</h3>
  <div class="PatchNotes-section PatchNotes-section-generic_update">
    <h4 class="PatchNotes-sectionTitle">Patch Notes</h4>
    <div class="PatchNotes-sectionDescription"><p>This is a February live patch.</p></div>
  </div>
</div>
"""


class GameUpdateParserTests(TestCase):
    def test_parse_game_updates_html_extracts_patch_entries(self):
        parsed = parse_game_updates_html(PATCH_NOTES_SAMPLE_HTML)

        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]['type_label'], 'Hotfix')
        self.assertEqual(parsed[0]['hero_image_url'], 'https://example.com/roadhog.png')
        self.assertEqual(parsed[0]['summary'], 'This is a balance hotfix update.')
        self.assertTrue(any(block['type'] == 'heading' and block['text'] == 'Roadhog' for block in parsed[0]['content_json']))
        self.assertTrue(any(block['type'] == 'bullet_list' for block in parsed[0]['content_json']))
        self.assertTrue(parsed[0]['source_url'].endswith('#patch-2026-04-23'))
        self.assertEqual(parsed[1]['type_label'], 'Bug Fix')

    def test_extract_archive_months_reads_live_archive_keys(self):
        self.assertEqual(
            extract_archive_months(PATCH_NOTES_ROOT_HTML),
            ['2026-04', '2026-03', '2026-02'],
        )

    @patch('scheduler.game_updates.requests.get')
    def test_sync_game_updates_upserts_records(self, mocked_get):
        def fake_response(text):
            response = Mock(status_code=200)
            response.raise_for_status = Mock()
            response.text = text
            return response

        url_map = {
            'https://overwatch.blizzard.com/en-us/news/patch-notes/': PATCH_NOTES_ROOT_HTML,
            'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/04': PATCH_NOTES_SAMPLE_HTML,
            'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/03': PATCH_NOTES_ARCHIVE_MARCH_HTML,
        }

        mocked_get.side_effect = lambda url, timeout=20: fake_response(url_map[url])

        first_result = sync_game_updates()

        self.assertEqual(first_result['created'], 3)
        self.assertEqual(first_result['updated'], 0)
        self.assertEqual(GameUpdate.objects.count(), 3)

        url_map['https://overwatch.blizzard.com/en-us/news/patch-notes/'] = PATCH_NOTES_ROOT_HTML.replace(
            'This is a balance hotfix update.',
            'This is an updated balance hotfix summary.',
        )
        url_map['https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/04'] = PATCH_NOTES_SAMPLE_HTML.replace(
            'This is a balance hotfix update.',
            'This is an updated balance hotfix summary.',
        )

        second_result = sync_game_updates()

        self.assertEqual(second_result['created'], 0)
        self.assertEqual(second_result['updated'], 3)
        self.assertEqual(GameUpdate.objects.count(), 3)
        self.assertEqual(
            GameUpdate.objects.get(slug='2026-04-23-overwatch-retail-patch-notes-april-23-2026').summary,
            'This is an updated balance hotfix summary.',
        )

    @patch('scheduler.game_updates.requests.get')
    def test_sync_game_updates_full_archive_imports_older_live_months(self, mocked_get):
        def fake_response(text):
            response = Mock(status_code=200)
            response.raise_for_status = Mock()
            response.text = text
            return response

        url_map = {
            'https://overwatch.blizzard.com/en-us/news/patch-notes/': PATCH_NOTES_ROOT_HTML,
            'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/04': PATCH_NOTES_SAMPLE_HTML,
            'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/03': PATCH_NOTES_ARCHIVE_MARCH_HTML,
            'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/02': PATCH_NOTES_ARCHIVE_FEB_HTML,
        }

        mocked_get.side_effect = lambda url, timeout=20: fake_response(url_map[url])

        result = sync_game_updates(full_archive=True)

        self.assertEqual(result['created'], 4)
        self.assertEqual(result['fetched'], 4)
        self.assertTrue(
            GameUpdate.objects.filter(
                slug='2026-02-25-overwatch-retail-patch-notes-february-25-2026'
            ).exists()
        )


class GameUpdateApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='updates-user', password='secret-pass')
        self.client.login(username='updates-user', password='secret-pass')
        self.update = GameUpdate.objects.create(
            slug='2026-04-23-overwatch-retail-patch-notes-april-23-2026',
            title='Overwatch Retail Patch Notes – April 23, 2026',
            published_at=date(2026, 4, 23),
            type_label='Hotfix',
            source_url='https://overwatch.blizzard.com/en-us/news/patch-notes/#patch-2026-04-23',
            summary='This is a balance hotfix update.',
            hero_image_url='https://example.com/roadhog.png',
            content_json=[{'type': 'paragraph', 'text': 'This is a balance hotfix update.'}],
        )

    def test_list_endpoint_returns_updates(self):
        response = self.client.get(reverse('api_game_updates_list'))

        self.assertEqual(response.status_code, 200)
        payload = response.json()['updates'][0]
        self.assertEqual(payload['slug'], self.update.slug)
        self.assertEqual(payload['typeLabel'], 'Hotfix')

    def test_detail_endpoint_returns_content_json(self):
        response = self.client.get(reverse('api_game_update_detail', args=[self.update.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['update']['contentJson'][0]['text'], 'This is a balance hotfix update.')

    def test_detail_endpoint_returns_404_for_missing_slug(self):
        response = self.client.get(reverse('api_game_update_detail', args=['missing-slug']))

        self.assertEqual(response.status_code, 404)


@override_settings(CRON_SECRET='sync-secret')
class GameUpdateSyncEndpointTests(TestCase):
    def test_sync_endpoint_rejects_missing_secret(self):
        response = self.client.get(reverse('api_game_updates_sync'))

        self.assertEqual(response.status_code, 401)

    @patch('scheduler.api_updates.sync_game_updates')
    def test_sync_endpoint_accepts_bearer_secret(self, mocked_sync):
        mocked_sync.return_value = {'fetched': 4, 'created': 2, 'updated': 2, 'total': 4}

        response = self.client.get(
            reverse('api_game_updates_sync'),
            HTTP_AUTHORIZATION='Bearer sync-secret',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['created'], 2)
