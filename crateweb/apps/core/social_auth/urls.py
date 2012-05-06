from django.conf.urls import patterns, url

from core.social_auth.views import SocialAuths

urlpatterns = patterns("",
    url(r"^social/$", SocialAuths.as_view(), name="social_auth_accounts"),
)
