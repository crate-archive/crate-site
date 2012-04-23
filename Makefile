LOCALE=en

makemessages:
	pybabel extract -F .babel.cfg --msgid-bugs-address support@crate.io --copyright-holder Crate --project Crate -o locale/messages.pot .
	pybabel update -D django -i locale/messages.pot -d locale -l en

compilemessages:
	pybabel compile -D django -i locale/$(LOCALE)/LC_MESSAGES/django.po -d locale -l $(LOCALE)
