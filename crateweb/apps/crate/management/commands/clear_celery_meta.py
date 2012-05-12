import redis

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        r = redis.StrictRedis(
            host=settings.REDIS['default']['HOST'],
            port=settings.REDIS['default']['PORT'],
            password=settings.REDIS['default']['PASSWORD'])
        i = 0
        for key in r.keys("celery-*"):
            r.delete(key)
            i += 1
        print "%d keys cleared" % i
