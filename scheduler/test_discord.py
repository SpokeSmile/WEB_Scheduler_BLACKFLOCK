from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import DiscordConnection, Player, StaffMember


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

    @patch('scheduler.api_discord.requests.get')
    @patch('scheduler.api_discord.requests.post')
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

    @patch('scheduler.api_discord.requests.get')
    @patch('scheduler.api_discord.requests.post')
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

    @patch('scheduler.api_discord.requests.get')
    @patch('scheduler.api_discord.requests.post')
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

    @patch('scheduler.api_discord.requests.get')
    @patch('scheduler.api_discord.requests.post')
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
