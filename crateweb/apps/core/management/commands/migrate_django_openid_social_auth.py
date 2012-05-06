from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from django.contrib.auth.models import User

from account.models import EmailAddress
from social_auth.models import UserSocialAuth


class Command(BaseCommand):

    def handle(self, *args, **options):
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, openid FROM django_openid_useropenidassociation;")

        for openid in cursor.fetchall():
            user = User.objects.get(pk=openid[0])
            print user.username, openid[1]
            UserSocialAuth.objects.get_or_create(provider="openid", uid=openid[1], defaults={"user": user})
