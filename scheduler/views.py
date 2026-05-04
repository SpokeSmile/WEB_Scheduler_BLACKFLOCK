from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from .roster import ensure_current_roster_week


@ensure_csrf_cookie
@login_required
def main_view(request):
    ensure_current_roster_week()
    return render(request, 'scheduler/app.html')


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


@ensure_csrf_cookie
@login_required
def team_view(request):
    ensure_current_roster_week()
    return render(request, 'scheduler/app.html')


@ensure_csrf_cookie
@login_required
def updates_view(request):
    ensure_current_roster_week()
    return render(request, 'scheduler/app.html')


@ensure_csrf_cookie
@login_required
def stats_view(request):
    ensure_current_roster_week()
    return render(request, 'scheduler/app.html')
