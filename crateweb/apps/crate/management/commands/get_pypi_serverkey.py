import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(
            host=settings.REDIS['default']['HOST'],
            port=settings.REDIS['default']['PORT'],
            password=settings.REDIS['default']['PASSWORD'])
        print r.get("crate:pypi:serverkey")
        print r.hgetall("crate:pypi:serverkey:headers")
