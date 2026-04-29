import mimetypes

from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import DayEventType, Player, RosterState, ScheduleSlot, StaffMember
from .roster import ensure_current_roster_week


MAX_AVATAR_SIZE_BYTES = 2 * 1024 * 1024


class PlayerAdminForm(forms.ModelForm):
    avatar_upload = forms.FileField(
        label='аватар файлом',
        required=False,
        help_text='Загрузите изображение. Файл будет сохранен прямо в базе данных.',
    )
    remove_uploaded_avatar = forms.BooleanField(
        label='удалить загруженный аватар',
        required=False,
    )

    class Meta:
        model = Player
        fields = '__all__'
        widgets = {
            'role_color': forms.TextInput(attrs={'type': 'color'}),
        }

    def clean_avatar_upload(self):
        avatar_upload = self.cleaned_data.get('avatar_upload')
        if not avatar_upload:
            return avatar_upload

        content_type = (
            getattr(avatar_upload, 'content_type', '')
            or mimetypes.guess_type(getattr(avatar_upload, 'name', ''))[0]
            or ''
        )
        if not content_type.startswith('image/'):
            raise forms.ValidationError('Нужен файл изображения.')
        if avatar_upload.size > MAX_AVATAR_SIZE_BYTES:
            raise forms.ValidationError('Максимальный размер аватара 2 МБ.')

        return avatar_upload

    def save(self, commit=True):
        player = super().save(commit=False)

        if self.cleaned_data.get('remove_uploaded_avatar'):
            player.clear_embedded_avatar()

        avatar_upload = self.cleaned_data.get('avatar_upload')
        if avatar_upload:
            player.set_embedded_avatar(avatar_upload)

        if commit:
            player.save()
            self.save_m2m()
        return player


class AvatarAdminMixin:
    readonly_fields = ('avatar_preview',)

    @admin.display(description='превью')
    def avatar_preview(self, obj):
        if not obj or not obj.resolved_avatar_url:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="width:72px;height:72px;border-radius:50%;object-fit:cover;border:1px solid rgba(0,0,0,.08);" />',
            obj.resolved_avatar_url,
        )


class StaffMemberAdminForm(forms.ModelForm):
    class Meta:
        model = StaffMember
        fields = '__all__'
        widgets = {
            'role_color': forms.TextInput(attrs={'type': 'color'}),
        }


class PlayerInline(AvatarAdminMixin, admin.StackedInline):
    model = Player
    form = PlayerAdminForm
    extra = 0
    max_num = 1
    fields = (
        'name',
        'role',
        'role_color',
        'sort_order',
        'avatar_preview',
        'avatar_upload',
        'remove_uploaded_avatar',
        'avatar_link',
        'battle_tags',
        'discord_tag',
    )
    verbose_name = 'профиль игрока'
    verbose_name_plural = 'профиль игрока'


admin.site.unregister(User)


@admin.register(User)
class PlayerUserAdmin(UserAdmin):
    inlines = (PlayerInline,)


@admin.register(Player)
class PlayerAdmin(AvatarAdminMixin, admin.ModelAdmin):
    form = PlayerAdminForm
    list_display = ('name', 'sort_order', 'role', 'role_color', 'user', 'discord_tag', 'avatar_preview')
    list_editable = ('sort_order', 'role_color')
    search_fields = ('name', 'role', 'user__username', 'discord_tag', 'battle_tags')
    fields = (
        'name',
        'role',
        'role_color',
        'sort_order',
        'user',
        'avatar_preview',
        'avatar_upload',
        'remove_uploaded_avatar',
        'avatar_link',
        'battle_tags',
        'discord_tag',
    )


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    form = StaffMemberAdminForm
    list_display = ('name', 'sort_order', 'role', 'role_color', 'discord_tag')
    list_editable = ('sort_order', 'role_color')
    search_fields = ('name', 'role', 'discord_tag')
    fields = ('name', 'role', 'role_color', 'sort_order', 'discord_tag')


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
