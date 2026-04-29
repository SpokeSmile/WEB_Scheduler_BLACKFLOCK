from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie

from .forms import ScheduleSlotForm
from .models import Player, ScheduleSlot
from .roster import ensure_current_roster_week


def get_current_player(user):
    return Player.objects.filter(user=user).first()


def get_current_staff_member(user):
    from .models import StaffMember

    return StaffMember.objects.filter(user=user).first()


@ensure_csrf_cookie
@login_required
def schedule_view(request):
    ensure_current_roster_week()
    return render(request, 'scheduler/app.html')


@ensure_csrf_cookie
@login_required
def profile_view(request):
    ensure_current_roster_week()
    return render(request, 'scheduler/app.html')


@login_required
def slot_create(request):
    ensure_current_roster_week()
    current_player = get_current_player(request.user)

    if current_player is None:
        messages.error(request, 'Ваш аккаунт не привязан к игроку. Обратитесь к администратору.')
        return redirect('schedule')

    initial = {}
    if request.GET.get('day') in {str(value) for value, _ in ScheduleSlot.DAY_CHOICES}:
        initial['day_of_week'] = int(request.GET['day'])

    form = ScheduleSlotForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        slot = form.save(commit=False)
        slot.player = current_player
        slot.full_clean()
        slot.save()
        messages.success(request, 'Запись добавлена в расписание.')
        return redirect('schedule')

    return render(request, 'scheduler/slot_form.html', {
        'form': form,
        'title': 'Добавить время',
        'submit_label': 'Добавить',
    })


@login_required
def slot_edit(request, pk):
    ensure_current_roster_week()
    current_player = get_current_player(request.user)
    slot = get_object_or_404(ScheduleSlot, pk=pk, player=current_player)
    form = ScheduleSlotForm(request.POST or None, instance=slot)

    if request.method == 'POST' and form.is_valid():
        slot = form.save(commit=False)
        slot.player = current_player
        slot.full_clean()
        slot.save()
        messages.success(request, 'Запись обновлена.')
        return redirect('schedule')

    return render(request, 'scheduler/slot_form.html', {
        'form': form,
        'title': 'Редактировать время',
        'submit_label': 'Сохранить',
    })


@login_required
def slot_delete(request, pk):
    ensure_current_roster_week()
    current_player = get_current_player(request.user)
    slot = get_object_or_404(ScheduleSlot, pk=pk, player=current_player)

    if request.method == 'POST':
        slot.delete()
        messages.success(request, 'Запись удалена.')
        return redirect('schedule')

    return render(request, 'scheduler/slot_confirm_delete.html', {'slot': slot})


def next_url_or_schedule(request):
    return request.POST.get('next') or request.GET.get('next') or reverse('schedule')
