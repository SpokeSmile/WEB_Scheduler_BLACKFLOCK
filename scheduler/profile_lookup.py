from .models import Player, StaffMember


def get_current_player(user):
    return Player.objects.filter(user=user).first()


def get_current_staff_member(user):
    return StaffMember.objects.filter(user=user).first()
