from django.contrib import admin
from core.models import UserAgent


class UserAgentAdmin(admin.ModelAdmin):
    list_display = ["short"]


admin.site.register(UserAgent, UserAgentAdmin)
