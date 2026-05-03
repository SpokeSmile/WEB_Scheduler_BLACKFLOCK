from datetime import date, timedelta

from django.db import migrations, models

import scheduler.models


def fallback_week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())


def populate_week_start(apps, schema_editor):
    RosterState = apps.get_model('scheduler', 'RosterState')
    DayEventType = apps.get_model('scheduler', 'DayEventType')

    state = RosterState.objects.filter(pk=1).first()
    week_start = state.current_week_start if state and state.current_week_start else fallback_week_start()
    DayEventType.objects.filter(week_start__isnull=True).update(week_start=week_start)


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0020_scheduleslot_week_start'),
    ]

    operations = [
        migrations.AddField(
            model_name='dayeventtype',
            name='week_start',
            field=models.DateField(blank=True, db_index=True, null=True, verbose_name='неделя'),
        ),
        migrations.RunPython(populate_week_start, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='dayeventtype',
            name='day_of_week',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, 'Понедельник'),
                    (1, 'Вторник'),
                    (2, 'Среда'),
                    (3, 'Четверг'),
                    (4, 'Пятница'),
                    (5, 'Суббота'),
                    (6, 'Воскресенье'),
                ],
                verbose_name='день недели',
            ),
        ),
        migrations.AlterField(
            model_name='dayeventtype',
            name='week_start',
            field=models.DateField(default=scheduler.models.default_week_start, db_index=True, verbose_name='неделя'),
        ),
        migrations.AlterModelOptions(
            name='dayeventtype',
            options={
                'ordering': ['week_start', 'day_of_week'],
                'verbose_name': 'тип события дня',
                'verbose_name_plural': 'типы событий по дням',
            },
        ),
        migrations.AddConstraint(
            model_name='dayeventtype',
            constraint=models.UniqueConstraint(fields=('week_start', 'day_of_week'), name='unique_day_event_type_per_week'),
        ),
    ]
