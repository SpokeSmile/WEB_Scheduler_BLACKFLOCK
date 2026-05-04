from django.urls import path

from . import api
from . import views

urlpatterns = [
    path('main/', views.main_view, name='main'),
    path('', views.schedule_view, name='schedule'),
    path('team/', views.team_view, name='team'),
    path('profile/', views.profile_view, name='profile'),
    path('updates/', views.updates_view, name='updates'),
    path('stats/', views.stats_view, name='stats'),
    path('api/bootstrap/', api.bootstrap, name='api_bootstrap'),
    path('api/game-updates/', api.game_updates_list, name='api_game_updates_list'),
    path('api/game-updates/sync/', api.game_updates_sync, name='api_game_updates_sync'),
    path('api/game-updates/<slug:slug>/', api.game_update_detail, name='api_game_update_detail'),
    path('api/overwatch-stats/', api.overwatch_stats, name='api_overwatch_stats'),
    path('api/overwatch-stats/refresh/', api.overwatch_stats_refresh, name='api_overwatch_stats_refresh'),
    path('api/slots/', api.slot_create, name='api_slot_create'),
    path('api/slots/<int:pk>/', api.slot_update, name='api_slot_update'),
    path('api/slots/<int:pk>/delete/', api.slot_delete, name='api_slot_delete'),
    path('api/profile/', api.profile_update, name='api_profile_update'),
    path('api/profile/password/', api.change_password, name='api_profile_password'),
    path('api/discord/connect/', api.discord_connect, name='api_discord_connect'),
    path('api/discord/callback/', api.discord_callback, name='api_discord_callback'),
    path('api/discord/disconnect/', api.discord_disconnect, name='api_discord_disconnect'),
    path('api/logout/', api.logout_view, name='api_logout'),
]
