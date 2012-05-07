from django.conf import settings
from django.core.management.base import BaseCommand

from django.contrib.auth.models import User


class Command(BaseCommand):

    def handle(self, *args, **options):
        if not settings.DEBUG:
            print "Dummy Passwords Only Available when DEBUG = True"
            return

        first_user = User.objects.all()[:1].get()
        first_user.set_password("letmein")
        first_user.save()

        User.objects.all().update(password=first_user.password)

