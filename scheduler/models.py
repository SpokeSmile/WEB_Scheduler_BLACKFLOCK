import base64
import mimetypes

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Укажите цвет в формате #RRGGBB.',
)

DEFAULT_ROLE_COLOR = '#4b607f'


class DiscordConnection(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='аккаунт',
        on_delete=models.CASCADE,
        related_name='discord_connection',
    )
    discord_user_id = models.CharField('discord user id', max_length=32, unique=True)
    username = models.CharField('discord username', max_length=80)
    global_name = models.CharField('discord global name', max_length=80, blank=True)
    avatar_hash = models.CharField('discord avatar hash', max_length=120, blank=True)
    connected_at = models.DateTimeField('подключено', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'подключение Discord'
        verbose_name_plural = 'подключения Discord'

    def __str__(self):
        return f'@{self.username}'

    @property
    def display_tag(self):
        return f'@{self.username}' if self.username else ''

    @property
    def avatar_url(self):
        if not self.avatar_hash:
            return ''
        return f'https://cdn.discordapp.com/avatars/{self.discord_user_id}/{self.avatar_hash}.png?size=128'


class Player(models.Model):
    name = models.CharField('имя игрока', max_length=80)
    role = models.CharField('роль', max_length=80, blank=True)
    role_color = models.CharField(
        'цвет роли',
        max_length=7,
        default=DEFAULT_ROLE_COLOR,
        validators=[HEX_COLOR_VALIDATOR],
    )
    sort_order = models.PositiveSmallIntegerField('порядок в таблице', default=0)
    avatar = models.FileField('аватар', upload_to='avatars/', blank=True)
    avatar_link = models.URLField(
        'ссылка на аватар',
        blank=True,
        help_text='Для продакшена на Vercel используйте прямую ссылку на изображение.',
    )
    avatar_data = models.BinaryField('данные аватара', blank=True, null=True, editable=False)
    avatar_content_type = models.CharField(
        'mime тип аватара',
        max_length=80,
        blank=True,
        editable=False,
    )
    battle_tags = models.TextField(
        'battle tags',
        blank=True,
        help_text='Указывайте по одному BattleTag на строку.',
    )
    discord_tag = models.CharField('discord тег', max_length=120, blank=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='аккаунт',
        on_delete=models.SET_NULL,
        related_name='player_profile',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'игрок'
        verbose_name_plural = 'игроки'

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.user and StaffMember.objects.filter(user=self.user).exclude(pk=getattr(self, 'pk', None)).exists():
            raise ValidationError({'user': 'Этот аккаунт уже привязан к организаторскому составу.'})

    @property
    def initial(self):
        return (self.name.strip()[:1] or '?').upper()

    @property
    def discord_connection(self):
        if not self.user_id:
            return None
        try:
            return self.user.discord_connection
        except DiscordConnection.DoesNotExist:
            return None

    @property
    def battle_tags_list(self):
        return [tag.strip() for tag in self.battle_tags.splitlines() if tag.strip()]

    def clear_embedded_avatar(self):
        self.avatar_data = None
        self.avatar_content_type = ''

    def set_embedded_avatar(self, uploaded_file):
        uploaded_file.seek(0)
        payload = uploaded_file.read()
        self.avatar_data = payload
        self.avatar_content_type = (
            getattr(uploaded_file, 'content_type', '')
            or mimetypes.guess_type(getattr(uploaded_file, 'name', ''))[0]
            or 'image/png'
        )

    @property
    def resolved_avatar_url(self):
        if self.avatar_data and self.avatar_content_type:
            encoded = base64.b64encode(bytes(self.avatar_data)).decode('ascii')
            return f'data:{self.avatar_content_type};base64,{encoded}'
        if self.avatar_link:
            return self.avatar_link
        if self.avatar:
            return self.avatar.url
        return ''


class StaffMember(models.Model):
    name = models.CharField('имя', max_length=80)
    role = models.CharField('роль', max_length=80)
    role_color = models.CharField(
        'цвет роли',
        max_length=7,
        default=DEFAULT_ROLE_COLOR,
        validators=[HEX_COLOR_VALIDATOR],
    )
    discord_tag = models.CharField('discord тег', max_length=120, blank=True)
    sort_order = models.PositiveSmallIntegerField('порядок в списке', default=0)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name='аккаунт',
        on_delete=models.SET_NULL,
        related_name='staff_profile',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['sort_order', 'id']
        verbose_name = 'организаторский состав'
        verbose_name_plural = 'организаторский состав'

    def __str__(self):
        return f'{self.name} — {self.role}'

    def clean(self):
        super().clean()
        if self.user and Player.objects.filter(user=self.user).exclude(pk=getattr(self, 'pk', None)).exists():
            raise ValidationError({'user': 'Этот аккаунт уже привязан к игроку.'})

    @property
    def initial(self):
        return (self.name.strip()[:1] or '?').upper()

    @property
    def discord_connection(self):
        if not self.user_id:
            return None
        try:
            return self.user.discord_connection
        except DiscordConnection.DoesNotExist:
            return None


class ScheduleSlot(models.Model):
    AVAILABLE = 'available'
    UNAVAILABLE = 'unavailable'
    FULL_DAY_AVAILABLE = 'full_day_available'
    TENTATIVE = 'tentative'

    SCRIM = 'scrim'
    COMPETITIVE = 'competitive'
    REVIEW = 'review'
    TOURNAMENT = 'tournament'

    SLOT_TYPE_CHOICES = [
        (AVAILABLE, 'Диапазон времени'),
        (FULL_DAY_AVAILABLE, 'Свободен весь день'),
        (TENTATIVE, 'Не уверен'),
        (UNAVAILABLE, 'Не могу в этот день'),
    ]

    EVENT_TYPE_CHOICES = [
        (TOURNAMENT, 'Tournament'),
        (SCRIM, 'Scrim'),
        (COMPETITIVE, 'Competitive'),
        (REVIEW, 'VOD Review'),
    ]

    EVENT_TYPE_META = {
        SCRIM: {
            'label': 'Scrim',
            'description': 'Тренировочный матч',
            'tone': 'blue',
        },
        COMPETITIVE: {
            'label': 'Competitive',
            'description': 'Соревновательная игра',
            'tone': 'orange',
        },
        REVIEW: {
            'label': 'VOD Review',
            'description': 'Разбор сыгранных карт и матчей',
            'tone': 'purple',
        },
        TOURNAMENT: {
            'label': 'Tournament',
            'description': 'Официальные турнирные матчи',
            'tone': 'red',
        },
    }

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    DAY_CHOICES = [
        (MONDAY, 'Понедельник'),
        (TUESDAY, 'Вторник'),
        (WEDNESDAY, 'Среда'),
        (THURSDAY, 'Четверг'),
        (FRIDAY, 'Пятница'),
        (SATURDAY, 'Суббота'),
        (SUNDAY, 'Воскресенье'),
    ]

    player = models.ForeignKey(
        Player,
        verbose_name='игрок',
        on_delete=models.CASCADE,
        related_name='slots',
    )
    slot_type = models.CharField(
        'тип записи',
        max_length=24,
        choices=SLOT_TYPE_CHOICES,
        default=AVAILABLE,
    )
    day_of_week = models.PositiveSmallIntegerField('день недели', choices=DAY_CHOICES)
    start_time_minutes = models.PositiveSmallIntegerField('начало', blank=True, null=True)
    end_time_minutes = models.PositiveSmallIntegerField('конец', blank=True, null=True)
    note = models.CharField('комментарий', max_length=160, blank=True)
    created_at = models.DateTimeField('создано', auto_now_add=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        ordering = ['player_id', 'day_of_week', 'start_time_minutes']
        verbose_name = 'слот расписания'
        verbose_name_plural = 'слоты расписания'
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        slot_type='available',
                        start_time_minutes__isnull=False,
                        start_time_minutes__gte=0,
                        start_time_minutes__lte=1380,
                        end_time_minutes__isnull=False,
                        end_time_minutes__gte=60,
                        end_time_minutes__lte=1440,
                        end_time_minutes__gt=models.F('start_time_minutes'),
                    )
                    | Q(
                        slot_type='full_day_available',
                        start_time_minutes__isnull=True,
                        end_time_minutes__isnull=True,
                    )
                    | Q(
                        slot_type='tentative',
                        start_time_minutes__isnull=True,
                        end_time_minutes__isnull=True,
                    )
                    | Q(
                        slot_type='unavailable',
                        start_time_minutes__isnull=True,
                        end_time_minutes__isnull=True,
                    )
                ),
                name='slot_valid_by_type',
            ),
        ]

    def __str__(self):
        return f'{self.player} - {self.get_day_of_week_display()} {self.label}'

    @staticmethod
    def format_minutes(value):
        if value is None:
            return ''
        hours = value // 60
        minutes = value % 60
        return f'{hours:02d}:{minutes:02d}'

    @property
    def start_label(self):
        return self.format_minutes(self.start_time_minutes)

    @property
    def end_label(self):
        return self.format_minutes(self.end_time_minutes)

    @property
    def time_range(self):
        return f'{self.start_label}-{self.end_label}'

    @property
    def is_available(self):
        return self.slot_type == self.AVAILABLE

    @property
    def is_unavailable(self):
        return self.slot_type == self.UNAVAILABLE

    @property
    def is_full_day_available(self):
        return self.slot_type == self.FULL_DAY_AVAILABLE

    @property
    def is_tentative(self):
        return self.slot_type == self.TENTATIVE

    @property
    def label(self):
        if self.is_full_day_available:
            return 'Свободен весь день'
        if self.is_tentative:
            return 'Не уверен'
        if self.is_unavailable:
            return 'Не могу в этот день'
        return 'Событие'

    @classmethod
    def event_types_payload(cls):
        return [
            {
                'value': value,
                'label': cls.EVENT_TYPE_META[value]['label'],
                'description': cls.EVENT_TYPE_META[value]['description'],
                'tone': cls.EVENT_TYPE_META[value]['tone'],
            }
            for value, _label in cls.EVENT_TYPE_CHOICES
        ]

    @classmethod
    def valid_event_type_values(cls):
        return {value for value, _label in cls.EVENT_TYPE_CHOICES}

    @property
    def display_note(self):
        if self.note:
            return self.note
        if self.is_available:
            return self.label
        return self.time_range

    def clean(self):
        if self.slot_type in {self.UNAVAILABLE, self.FULL_DAY_AVAILABLE, self.TENTATIVE}:
            self.start_time_minutes = None
            self.end_time_minutes = None
            return


class RosterState(models.Model):
    current_week_start = models.DateField('текущая неделя', blank=True, null=True)
    last_reset_at = models.DateTimeField('последний сброс', blank=True, null=True)
    updated_at = models.DateTimeField('обновлено', auto_now=True)

    class Meta:
        verbose_name = 'состояние расписания'
        verbose_name_plural = 'состояние расписания'

    def __str__(self):
        return f'Roster state ({self.current_week_start or "not set"})'

        if self.start_time_minutes is None or self.end_time_minutes is None:
            raise ValidationError('Для диапазона времени нужно выбрать начало и конец.')

        if self.end_time_minutes <= self.start_time_minutes:
            raise ValidationError({'end_time_minutes': 'Время окончания должно быть позже начала.'})


class DayEventType(models.Model):
    day_of_week = models.PositiveSmallIntegerField(
        'день недели',
        choices=ScheduleSlot.DAY_CHOICES,
        unique=True,
    )
    event_type = models.CharField(
        'тип события',
        max_length=24,
        choices=[('', 'Без события')] + ScheduleSlot.EVENT_TYPE_CHOICES,
        blank=True,
        default='',
    )

    class Meta:
        ordering = ['day_of_week']
        verbose_name = 'тип события дня'
        verbose_name_plural = 'типы событий по дням'

    def __str__(self):
        return f'{self.get_day_of_week_display()} - {self.event_label or "Без события"}'

    @property
    def event_label(self):
        return ScheduleSlot.EVENT_TYPE_META.get(self.event_type, {}).get('label', '')

    @property
    def event_description(self):
        return ScheduleSlot.EVENT_TYPE_META.get(self.event_type, {}).get('description', '')

    @property
    def event_tone(self):
        return ScheduleSlot.EVENT_TYPE_META.get(self.event_type, {}).get('tone', 'orange')


class GameUpdate(models.Model):
    slug = models.SlugField('slug', max_length=180, unique=True)
    title = models.CharField('заголовок', max_length=255)
    published_at = models.DateField('дата публикации')
    type_label = models.CharField('тип обновления', max_length=80)
    source_url = models.URLField('источник', max_length=500)
    summary = models.TextField('краткое описание', blank=True)
    hero_image_url = models.URLField('изображение героя', max_length=500, blank=True)
    content_json = models.JSONField('контент патча', default=list, blank=True)
    synced_at = models.DateTimeField('синхронизировано', auto_now=True)

    class Meta:
        ordering = ['-published_at', '-id']
        verbose_name = 'обновление игры'
        verbose_name_plural = 'обновления игры'

    def __str__(self):
        return self.title


class OverwatchStatsCache(models.Model):
    COMPETITIVE = 'competitive'

    STATUS_READY = 'ready'
    STATUS_ERROR = 'error'
    STATUS_MISSING_BATTLETAG = 'missing_battletag'

    MODE_CHOICES = [
        (COMPETITIVE, 'Competitive'),
    ]

    STATUS_CHOICES = [
        (STATUS_READY, 'Готово'),
        (STATUS_ERROR, 'Ошибка'),
        (STATUS_MISSING_BATTLETAG, 'BattleTag не указан'),
    ]

    player = models.ForeignKey(
        Player,
        verbose_name='игрок',
        on_delete=models.CASCADE,
        related_name='overwatch_stats_cache',
    )
    battle_tag = models.CharField('battle tag', max_length=120, blank=True)
    overfast_player_id = models.CharField('overfast player id', max_length=120, blank=True)
    mode = models.CharField('режим', max_length=20, choices=MODE_CHOICES)
    status = models.CharField('статус', max_length=32, choices=STATUS_CHOICES, default=STATUS_ERROR)
    error = models.CharField('ошибка', max_length=255, blank=True)
    summary_json = models.JSONField('summary json', default=dict, blank=True)
    stats_json = models.JSONField('stats json', default=dict, blank=True)
    fetched_at = models.DateTimeField('обновлено', null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['player', 'mode'], name='unique_overwatch_stats_cache_player_mode'),
        ]
        ordering = ['player__sort_order', 'overfast_player_id', 'mode']
        verbose_name = 'кэш статистики Overwatch'
        verbose_name_plural = 'кэш статистики Overwatch'

    def __str__(self):
        return f'{self.player} · {self.mode}'
