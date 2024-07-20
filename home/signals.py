from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Preference

@receiver(post_migrate)
def create_default_preference(sender, **kwargs):
    if not Preference.objects.exists():
        Preference.objects.create()
