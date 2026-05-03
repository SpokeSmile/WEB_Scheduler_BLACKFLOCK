from django.contrib import admin
from django.test import TestCase

from .admin import PlayerAdmin, PlayerInline, StaffMemberAdmin
from .models import Player, StaffMember


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
