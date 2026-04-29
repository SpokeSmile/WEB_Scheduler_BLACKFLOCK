from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import DayEventType, DiscordConnection, Player, RosterState, ScheduleSlot, StaffMember
from .roster import ensure_current_roster_week


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
    change_list_template = 'admin/scheduler/scheduleslot/change_list.html'
    list_display = ('player', 'slot_type', 'day_of_week', 'start_label', 'end_label', 'note')
    list_filter = ('player', 'slot_type', 'day_of_week')
    search_fields = ('player__name', 'note')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'reset-table/',
                self.admin_site.admin_view(self.reset_table_view),
                name='scheduler_scheduleslot_reset_table',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        state = RosterState.objects.filter(pk=1).first()
        extra_context = extra_context or {}
        extra_context['reset_table_url'] = reverse('admin:scheduler_scheduleslot_reset_table')
        extra_context['last_reset_at'] = state.last_reset_at if state else None
        extra_context['current_week_start'] = state.current_week_start if state else None
        return super().changelist_view(request, extra_context=extra_context)

    def reset_table_view(self, request):
        if request.method != 'POST':
            return HttpResponseRedirect(reverse('admin:scheduler_scheduleslot_changelist'))

        _changed, deleted_count = ensure_current_roster_week(force=True)
        messages.success(request, f'Таблица времени очищена. Удалено записей: {deleted_count}.')
        return HttpResponseRedirect(reverse('admin:scheduler_scheduleslot_changelist'))


@admin.register(DayEventType)
class DayEventTypeAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'event_type', 'event_label')
    list_filter = ('event_type',)
