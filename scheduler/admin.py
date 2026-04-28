from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import DayEventType, Player, ScheduleSlot


class PlayerInline(admin.StackedInline):
    model = Player
    extra = 0
    max_num = 1
    fields = ('name', 'role', 'avatar', 'battle_tags', 'discord_tag')
    verbose_name = 'профиль игрока'
    verbose_name_plural = 'профиль игрока'


admin.site.unregister(User)


@admin.register(User)
class PlayerUserAdmin(UserAdmin):
    inlines = (PlayerInline,)


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'user', 'discord_tag', 'avatar')
    search_fields = ('name', 'role', 'user__username', 'discord_tag', 'battle_tags')
    fields = ('name', 'role', 'user', 'avatar', 'battle_tags', 'discord_tag')


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ('player', 'slot_type', 'day_of_week', 'start_label', 'end_label', 'note')
    list_filter = ('player', 'slot_type', 'day_of_week')
    search_fields = ('player__name', 'note')


@admin.register(DayEventType)
class DayEventTypeAdmin(admin.ModelAdmin):
    list_display = ('day_of_week', 'event_type', 'event_label')
    list_filter = ('event_type',)
