LOCALE=en
DUMPPATH=$(HOME)/Dropbox/Crate/crate.dump
DBNAME=crate

makemessages:
	pybabel extract -F .babel.cfg --msgid-bugs-address support@crate.io --copyright-holder Crate --project Crate -o locale/messages.pot .
	pybabel update -D django -i locale/messages.pot -d locale -l en

compilemessages:
	pybabel compile -D django -i locale/$(LOCALE)/LC_MESSAGES/django.po -d locale -l $(LOCALE)

freshdb:
	dropdb crate
	createdb crate

reloaddb: freshdb
	pg_restore -d $(DBNAME) -j 8 --no-owner --no-acl $(DUMPPATH)

updb:
	python manage.py syncdb
	python manage.py migrate
	python manage.py dummy_passwords

serve:
	python manage.py runserver
