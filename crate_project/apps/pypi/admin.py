from django.contrib import admin

from pypi.models import PyPIMirrorPage, PyPIServerSigPage, PyPIIndexPage
from pypi.models import PyPIDownloadChange, URLLastModified


class PyPIMirrorPageAdmin(admin.ModelAdmin):
    list_display = ["package", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["package__name", "content"]
    raw_id_fields = ["package"]


class PyPIServerSigPageAdmin(admin.ModelAdmin):
    list_display = ["package", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["package__name", "content"]
    raw_id_fields = ["package"]


class PyPIIndexPageAdmin(admin.ModelAdmin):
    list_display = ["created", "modified"]
    list_filter = ["created", "modified"]


class PyPIDownloadChangeAdmin(admin.ModelAdmin):
    list_display = ["file", "change", "created", "modified"]
    list_filter = ["created", "modified"]
    search_fields = ["file__release__package__name"]
    raw_id_fields = ["file"]


class URLLastModifiedAdmin(admin.ModelAdmin):
    list_display = ["url", "last_modified"]
    search_fields = ["url", "last_modified"]


admin.site.register(PyPIMirrorPage, PyPIMirrorPageAdmin)
admin.site.register(PyPIServerSigPage, PyPIServerSigPageAdmin)
admin.site.register(PyPIIndexPage, PyPIIndexPageAdmin)
admin.site.register(PyPIDownloadChange, PyPIDownloadChangeAdmin)
admin.site.register(URLLastModified, URLLastModifiedAdmin)
