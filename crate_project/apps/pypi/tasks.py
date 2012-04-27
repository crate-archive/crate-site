import bz2
import collections
import csv
import datetime
import hashlib
import logging
import re
import socket
import StringIO
import time
import xmlrpclib

import lxml.html
import redis
import requests

from celery.task import task

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from crate.utils.lock import Lock
from packages.models import Package, ReleaseFile, TroveClassifier, DownloadDelta
from pypi.models import PyPIIndexPage, PyPIDownloadChange, URLLastModified
from pypi.processor import PyPIPackage

logger = logging.getLogger(__name__)

INDEX_URL = "http://pypi.python.org/pypi"

SERVERKEY_URL = "http://pypi.python.org/serverkey"
SERVERKEY_KEY = "crate:pypi:serverkey"

CLASSIFIER_URL = "http://pypi.python.org/pypi?%3Aaction=list_classifiers"

PYPI_SINCE_KEY = "crate:pypi:since"


def process(name, version, timestamp, action, matches):
    package = PyPIPackage(name, version)
    package.process()


def remove(name, version, timestamp, action, matches):
    package = PyPIPackage(name, version)
    package.delete()


def remove_file(name, version, timestamp, action, matches):
    package = PyPIPackage(name, version)
    package.remove_files(*matches.groups())


@task
def bulk_process(name, version, timestamp, action, matches):
    package = PyPIPackage(name)
    package.process(bulk=True)


@task
def bulk_synchronize():
    pypi = xmlrpclib.ServerProxy(INDEX_URL)

    names = set()

    for package in pypi.list_packages():
        names.add(package)
        bulk_process.delay(package, None, None, None, None)

    for package in Package.objects.exclude(name__in=names):
        package.delete()


@task
def synchronize(since=None):
    with Lock("synchronize", expires=60 * 5, timeout=30):
        datastore = redis.StrictRedis(**getattr(settings, "PYPI_DATASTORE_CONFIG", {}))

        if since is None:
            s = datastore.get(PYPI_SINCE_KEY)
            if s is not None:
                since = int(float(s)) - 30

        current = time.mktime(datetime.datetime.utcnow().timetuple())

        pypi = xmlrpclib.ServerProxy(INDEX_URL)

        headers = datastore.hgetall(SERVERKEY_KEY + ":headers")
        sig = requests.get(SERVERKEY_URL, headers=headers, prefetch=True)

        if not sig.status_code == 304:
            sig.raise_for_status()

            if sig.content != datastore.get(SERVERKEY_KEY):
                logger.error("Key Rollover Detected")
                pypi_key_rollover.delay()
                datastore.set(SERVERKEY_KEY, sig.content)

        datastore.hmset(SERVERKEY_KEY + ":headers", {"If-Modified-Since": sig.headers["Last-Modified"]})

        if since is None:  # @@@ Should we do this for more than just initial?
            bulk_synchronize.delay()
        else:
            logger.info("[SYNCING] Changes since %s" % since)
            changes = pypi.changelog(since)

            for name, version, timestamp, action in changes:
                line_hash = hashlib.sha256(":".join([str(x) for x in (name, version, timestamp, action)])).hexdigest()
                logdata = {"action": action, "name": name, "version": version, "timestamp": timestamp, "hash": line_hash}

                if not datastore.exists("crate:pypi:changelog:%s" % line_hash):
                    logger.debug("[PROCESS] %(name)s %(version)s %(timestamp)s %(action)s" % logdata)
                    logger.debug("[HASH] %(name)s %(version)s %(hash)s" % logdata)

                    dispatch = collections.OrderedDict([
                        (re.compile("^create$"), process),
                        (re.compile("^new release$"), process),
                        (re.compile("^add [\w\d\.]+ file .+$"), process),
                        (re.compile("^remove$"), remove),
                        (re.compile("^remove file (.+)$"), remove_file),
                        (re.compile("^update [\w]+(, [\w]+)*$"), process),
                        #(re.compile("^docupdate$"), docupdate),  # @@@ Do Something
                        #(re.compile("^add (Owner|Maintainer) .+$"), add_user_role),  # @@@ Do Something
                        #(re.compile("^remove (Owner|Maintainer) .+$"), remove_user_role),  # @@@ Do Something
                    ])

                    # Dispatch Based on the action
                    for pattern, func in dispatch.iteritems():
                        matches = pattern.search(action)
                        if matches is not None:
                            func(name, version, timestamp, action, matches)
                            break
                    else:
                        logger.warn("[UNHANDLED] %(name)s %(version)s %(timestamp)s %(action)s" % logdata)

                    datastore.setex("crate:pypi:changelog:%s" % line_hash, 2629743, datetime.datetime.utcnow().isoformat())
                else:
                    logger.debug("[SKIP] %(name)s %(version)s %(timestamp)s %(action)s" % logdata)
                    logger.debug("[HASH] %(name)s %(version)s %(hash)s" % logdata)

        datastore.set(PYPI_SINCE_KEY, current)


@task
def synchronize_troves():
    resp = requests.get(CLASSIFIER_URL)
    resp.raise_for_status()

    current_troves = set(TroveClassifier.objects.all().values_list("trove", flat=True))
    new_troves = set([x.strip() for x in resp.content.splitlines()]) - current_troves

    with transaction.commit_on_success():
        for classifier in new_troves:
            TroveClassifier.objects.get_or_create(trove=classifier)


@task
def synchronize_downloads():
    for package in Package.objects.all().order_by("downloads_synced_on").prefetch_related("releases", "releases__files")[:150]:
        Package.objects.filter(pk=package.pk).update(downloads_synced_on=now())

        for release in package.releases.all():
            update_download_counts.delay(package.name, release.version, dict([(x.filename, x.pk) for x in release.files.all()]))


@task
def update_download_counts(package_name, version, files, index=None):
    try:
        pypi = xmlrpclib.ServerProxy(INDEX_URL)

        downloads = pypi.release_downloads(package_name, version)

        for filename, download_count in downloads:
            if filename in files:
                with transaction.commit_on_success():
                    for releasefile in ReleaseFile.objects.filter(pk=files[filename]).select_for_update():
                        old = releasefile.downloads
                        releasefile.downloads = download_count
                        releasefile.save()

                        change = releasefile.downloads - old
                        if change:
                            PyPIDownloadChange.objects.create(file=releasefile, change=change)
    except socket.error:
        logger.exception("[DOWNLOAD SYNC] Network Error")


@task
def process_downloads():
    BASE_URL = "http://pypi.python.org/stats/days/"

    release_files = None

    session = requests.session()

    response = session.get(BASE_URL)
    response.raise_for_status()

    html = lxml.html.fromstring(response.text)
    html.make_links_absolute(BASE_URL)

    for link in html.xpath("//a/@href"):
        if not link.endswith(".bz2"):
            continue

        base, name = link.rsplit("/", 1)

        assert base.lower() == BASE_URL[:-1]

        date_string, _ = name.rsplit(".", 1)
        file_date = datetime.datetime.strptime(date_string, "%Y-%m-%d")

        print file_date

        try:
            umodified = URLLastModified.objects.get(url=link)
        except URLLastModified.DoesNotExist:
            headers = None
        else:
            headers = {
                "If-Modified-Since": umodified.last_modified,
            }

        # @@@ Check if Modified Since
        response = session.get(link, headers=headers, prefetch=True)

        if response.status_code == 304:
            # Skip this file as it hasn't changed
            print "SKIPPING"
            continue
        else:
            print "PROCESSING"

        response.raise_for_status()

        f = StringIO.StringIO(bz2.decompress(response.content))

        for line in csv.DictReader(f,  fieldnames=["package", "filename", "user_agent", "count"]):
            if release_files is None:
                release_files = dict(
                    [((x.release.package.name, x.filename), x) for x in ReleaseFile.objects.all().only(
                        "file", "filename", "release__package__name").select_related("release", "release__package")]
                )

            rf = release_files.get((line["package"], line["filename"]), None)

            if rf is None:
                # @@@ Store Historical Data
                continue

            delta, c = DownloadDelta.objects.get_or_create(
                            date=file_date,
                            file=rf,
                            user_agent=line.get("user_agent", ""),
                            defaults={"delta": int(line.get("count", 0))}
                        )

            if not c and delta.delta != line.get("count", 0):
                DownloadDelta.objects.filter(pk=delta.pk).update(delta=int(line.get("count", 0)))

        umodified, c = URLLastModified.objects.get_or_create(url=link, defaults={"last_modified": response.headers.get("Last-Modified")})

        if not c and umodified.last_modified != response.headers.get("Last-Modified"):
            URLLastModified.objects.filter(pk=umodified.pk).update(last_modified=response.headers.get("Last-Modified"))


@task
def pypi_key_rollover():
    datastore = redis.StrictRedis(**getattr(settings, "PYPI_DATASTORE_CONFIG", {}))

    sig = requests.get(SERVERKEY_URL, prefetch=True)
    sig.raise_for_status()

    datastore.set(SERVERKEY_KEY, sig.content)

    for package in Package.objects.all():
        fetch_server_key.delay(package.name)


@task
def fetch_server_key(package):
    p = PyPIPackage(package)
    p.verify_and_sync_pages()


@task
def refresh_pypi_package_index_cache():
    r = requests.get("http://pypi.python.org/simple/", prefetch=True)
    PyPIIndexPage.objects.create(content=r.content)
