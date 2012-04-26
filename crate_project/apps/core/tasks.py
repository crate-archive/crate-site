from django.db import transaction

from celery.task import task

from core.models import UserAgent
from packages.models import DownloadDelta


@task
def compact():
    agents = dict([(x.raw, x.short) for x in UserAgent.objects.all()])

    for ua, short in agents.iteritems():
        with transaction.commit_on_success():
            to_delete = set()

            for delta in DownloadDelta.objects.filter(user_agent=ua):
                if delta.delta != 0:
                    if delta.file_id:
                        d, c = DownloadDelta.objects.get_or_create(date=delta.date, file_id=delta.file_id, user_agent=short, defaults={"delta": delta.delta})

                        if not c:
                            DownloadDelta.objects.filter(pk=d.pk).update(d.delta + delta.delta)
                    elif delta.release_id:
                        d, c = DownloadDelta.objects.get_or_create(date=delta.date, release_id=delta.release_id, user_agent=short, defaults={"delta": delta.delta})

                        if not c:
                            DownloadDelta.objects.filter(pk=d.pk).update(d.delta + delta.delta)
                    elif delta.package_id:
                        d, c = DownloadDelta.objects.get_or_create(date=delta.date, package_id=delta.package_id, user_agent=short, defaults={"delta": delta.delta})

                        if not c:
                            DownloadDelta.objects.filter(pk=d.pk).update(d.delta + delta.delta)
                    else:
                        d, c = DownloadDelta.objects.get_or_create(package_id=None, release_id=None, file_id=None, package_name=delta.package_name, release_version=delta.release_version, filename=delta.filename, defaults={"delta": delta.delta})

                        if not c:
                            DownloadDelta.objects.filter(pk=d.pk).update(d.delta + delta.delta)
                to_delete.add(delta.pk)

            DownloadDelta.objects.filter(pk__in=to_delete).delete()
