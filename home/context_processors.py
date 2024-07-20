# context_processors.py

from .models import Preference

def preference(request):
    try:
        preference = Preference.objects.first()
    except Preference.DoesNotExist:
        preference = None
    return {'preference': preference}
