from django import forms

from .models import DayEventType, ScheduleSlot


def build_time_choices(start_hour, end_hour):
    return [
        (hour * 60, f'{hour:02d}:00')
        for hour in range(start_hour, end_hour + 1)
    ]


class ScheduleSlotForm(forms.ModelForm):
    slot_type = forms.ChoiceField(
        label='Тип',
        choices=ScheduleSlot.SLOT_TYPE_CHOICES,
    )
    day_of_week = forms.TypedChoiceField(
        label='День',
        choices=ScheduleSlot.DAY_CHOICES,
        coerce=int,
    )
    start_time_minutes = forms.TypedChoiceField(
        label='С',
        choices=build_time_choices(0, 23),
        coerce=int,
        empty_value=None,
        required=False,
    )
    end_time_minutes = forms.TypedChoiceField(
        label='До',
        choices=build_time_choices(1, 24),
        coerce=int,
        empty_value=None,
        required=False,
    )

    class Meta:
        model = ScheduleSlot
        fields = [
            'slot_type',
            'day_of_week',
            'start_time_minutes',
            'end_time_minutes',
            'note',
        ]
        widgets = {
            'note': forms.TextInput(attrs={'placeholder': 'Например: турнирный блок, поздний старт'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        slot_type = cleaned_data.get('slot_type')
        day_of_week = cleaned_data.get('day_of_week')
        start_time = cleaned_data.get('start_time_minutes')
        end_time = cleaned_data.get('end_time_minutes')

        if slot_type == ScheduleSlot.UNAVAILABLE:
            cleaned_data['start_time_minutes'] = None
            cleaned_data['end_time_minutes'] = None
            return cleaned_data

        if (
            day_of_week is not None
            and not DayEventType.objects.filter(day_of_week=day_of_week)
            .exclude(event_type='')
            .exists()
        ):
            self.add_error('day_of_week', 'Администратор должен настроить этот день перед добавлением времени.')

        if start_time is None:
            self.add_error('start_time_minutes', 'Выберите время начала.')

        if end_time is None:
            self.add_error('end_time_minutes', 'Выберите время окончания.')

        if start_time is not None and end_time is not None and end_time <= start_time:
            self.add_error('end_time_minutes', 'Время окончания должно быть позже начала.')

        return cleaned_data
