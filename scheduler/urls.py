from django.urls import path

from . import api
from . import views

urlpatterns = [
    path('', views.schedule_view, name='schedule'),
    path('api/bootstrap/', api.bootstrap, name='api_bootstrap'),
    path('api/slots/', api.slot_create, name='api_slot_create'),
    path('api/slots/<int:pk>/', api.slot_update, name='api_slot_update'),
    path('api/slots/<int:pk>/delete/', api.slot_delete, name='api_slot_delete'),
    path('api/profile/', api.profile_update, name='api_profile_update'),
    path('api/logout/', api.logout_view, name='api_logout'),
    path('slot/new/', views.slot_create, name='slot_create'),
    path('slot/<int:pk>/edit/', views.slot_edit, name='slot_edit'),
    path('slot/<int:pk>/delete/', views.slot_delete, name='slot_delete'),
]
