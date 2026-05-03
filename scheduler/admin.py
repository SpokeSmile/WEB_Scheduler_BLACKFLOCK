from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .game_updates import GameUpdateSyncError, sync_game_updates
from .models import DayEventType, DiscordConnection, GameUpdate, OverwatchStatsCache, Player, ScheduleSlot, StaffMember


class PlayerAdminForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = '__all__'
        widgets = {
            'role_color': forms.TextInput(attrs={'type': 'color'}),
        }


class DiscordConnectionAdminMixin:
    readonly_fields = (
        'discord_status',
        'discord_handle',
        'discord_global_name_display',
        'discord_connected_at_display',
        'discord_avatar_preview',
    )

    def get_discord_connection(self, obj):
        if obj is None:
            return None
        if isinstance(obj, DiscordConnection):
            return obj
        if hasattr(obj, 'discord_connection'):
            return obj.discord_connection
        return None

    @admin.display(description='статус Discord')
    def discord_status(self, obj):
        return 'Подключен' if self.get_discord_connection(obj) else 'Не подключен'

    @admin.display(description='Discord handle')
    def discord_handle(self, obj):
        connection = self.get_discord_connection(obj)
        return connection.display_tag if connection else '—'

    @admin.display(description='global name')
    def discord_global_name_display(self, obj):
        connection = self.get_discord_connection(obj)
        return connection.global_name if connection and connection.global_name else '—'

    @admin.display(description='подключено')
    def discord_connected_at_display(self, obj):
        connection = self.get_discord_connection(obj)
        return connection.connected_at if connection else '—'

    @admin.display(description='avatar preview')
    def discord_avatar_preview(self, obj):
        connection = self.get_discord_connection(obj)
        if not connection or not connection.avatar_url:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="width:72px;height:72px;border-radius:50%;object-fit:cover;border:1px solid rgba(0,0,0,.08);" />',
            connection.avatar_url,
        )


class StaffMemberAdminForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = '__all__'
        widgets = {
            'role_color': forms.TextInput(attrs={'type': 'color'}),
        }


class PlayerInline(DiscordConnectionAdminMixin, admin.StackedInline):
    model = Player
    form = PlayerAdminForm
    extra = 0
    max_num = 1
    fields = (
        'name',
        'role',
        'role_color',
        'sort_order',
        'discord_status',
        'discord_handle',
        'discord_global_name_display',
        'discord_connected_at_display',
        'discord_avatar_preview',
        'battle_tags',
    )
    verbose_name = 'профиль игрока'
    verbose_name_plural = 'профиль игрока'


admin.site.unregister(User)


@admin.register(User)
class PlayerUserAdmin(UserAdmin):
    inlines = (PlayerInline,)


@admin.register(Player)
class PlayerAdmin(DiscordConnectionAdminMixin, admin.ModelAdmin):
    form = PlayerAdminForm
    list_display = ('name', 'sort_order', 'role', 'role_color', 'user', 'discord_status', 'discord_handle')
    list_editable = ('sort_order', 'role_color')
    search_fields = ('name', 'role', 'user__username', 'battle_tags', 'user__discord_connection__username', 'user__discord_connection__global_name')
    fields = (
        'name',
        'role',
        'role_color',
        'sort_order',
        'user',
        'discord_status',
        'discord_handle',
        'discord_global_name_display',
        'discord_connected_at_display',
        'discord_avatar_preview',
        'battle_tags',
    )


@admin.register(StaffMember)
class StaffMemberAdmin(DiscordConnectionAdminMixin, admin.ModelAdmin):
    form = StaffMemberAdminForm
    list_display = ('name', 'sort_order', 'role', 'role_color', 'user', 'discord_status', 'discord_handle')
    list_editable = ('sort_order', 'role_color')
    search_fields = ('name', 'role', 'user__username', 'user__discord_connection__username', 'user__discord_connection__global_name')
    fields = (
        'name',
        'role',
        'role_color',
        'sort_order',
        'user',
        'discord_status',
        'discord_handle',
        'discord_global_name_display',
        'discord_connected_at_display',
        'discord_avatar_preview',
    )


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ('player', 'week_start', 'slot_type', 'day_of_week', 'start_label', 'end_label', 'note')
    list_filter = ('week_start', 'player', 'slot_type', 'day_of_week')
    search_fields = ('player__name', 'note')
    date_hierarchy = 'week_start'


@admin.register(DayEventType)
class DayEventTypeAdmin(admin.ModelAdmin):
    list_display = ('week_start', 'day_of_week', 'event_type', 'event_label')
    list_filter = ('week_start', 'event_type')
    date_hierarchy = 'week_start'


@admin.register(GameUpdate)
class GameUpdateAdmin(admin.ModelAdmin):
    change_list_template = 'admin/scheduler/gameupdate/change_list.html'
    list_display = ('title', 'published_at', 'type_label', 'synced_at')
    search_fields = ('title', 'summary', 'type_label', 'source_url')
    ordering = ('-published_at', '-id')
    readonly_fields = (
        'slug',
        'title',
        'published_at',
        'type_label',
        'source_link',
        'hero_image_preview',
        'summary',
        'content_preview',
        'synced_at',
    )
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'sync-updates/',
                self.admin_site.admin_view(self.sync_updates_view),
                name='scheduler_gameupdate_sync_updates',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['sync_updates_url'] = reverse('admin:scheduler_gameupdate_sync_updates')
        return super().changelist_view(request, extra_context=extra_context)

    def sync_updates_view(self, request):
        if request.method != 'POST':
            return HttpResponseRedirect(reverse('admin:scheduler_gameupdate_changelist'))

        try:
            result = sync_game_updates()
        except GameUpdateSyncError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f"Синхронизация завершена. Найдено: {result['fetched']}. Создано: {result['created']}. Обновлено: {result['updated']}.",
            )
        return HttpResponseRedirect(reverse('admin:scheduler_gameupdate_changelist'))

    @admin.display(description='источник')
    def source_link(self, obj):
        return format_html('<a href="{}" target="_blank" rel="noopener noreferrer">Открыть Blizzard</a>', obj.source_url)

    @admin.display(description='hero image')
    def hero_image_preview(self, obj):
        if not obj.hero_image_url:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="width:72px;height:72px;border-radius:12px;object-fit:cover;border:1px solid rgba(0,0,0,.08);" />',
            obj.hero_image_url,
        )

    @admin.display(description='контент')
    def content_preview(self, obj):
        return format_html('<pre style="white-space:pre-wrap;max-width:900px;">{}</pre>', obj.content_json)


@admin.register(OverwatchStatsCache)
class OverwatchStatsCacheAdmin(admin.ModelAdmin):
    list_display = ('player', 'mode', 'status', 'battle_tag', 'overfast_player_id', 'fetched_at')
    list_filter = ('mode', 'status')
    search_fields = ('player__name', 'battle_tag', 'overfast_player_id', 'error')
    readonly_fields = (
        'player',
        'battle_tag',
        'overfast_player_id',
        'mode',
        'status',
        'error',
        'summary_json',
        'stats_json',
        'fetched_at',
    )

    def has_add_permission(self, request):
        return False
