from social_auth.backends import SREG_ATTR, OLD_AX_ATTRS, AX_SCHEMA_ATTRS
from social_auth.backends import OpenIDBackend as BaseOpenIDBackend
from social_auth.backends import OpenIdAuth as BaseOpenIdAuth


class OpenIDBackend(BaseOpenIDBackend):

    def get_user_details(self, response):
        """Return user details from an OpenID request"""
        values = {"username": '', 'email': '', 'fullname': '',
                  'first_name': '', 'last_name': ''}
        # update values using SimpleRegistration or AttributeExchange
        # values
        values.update(self.values_from_response(response,
                                                SREG_ATTR,
                                                OLD_AX_ATTRS + \
                                                AX_SCHEMA_ATTRS))

        fullname = values.get('fullname') or ''
        first_name = values.get('first_name') or ''
        last_name = values.get('last_name') or ''

        if not fullname and first_name and last_name:
            fullname = first_name + ' ' + last_name
        elif fullname:
            try:  # Try to split name for django user storage
                first_name, last_name = fullname.rsplit(' ', 1)
            except ValueError:
                last_name = fullname

        values.update({
            'fullname': fullname,
            'first_name': first_name,
            'last_name': last_name,
            'username': values.get('username') or values.get('nickname') or (first_name.title() + last_name.title())
        })

        return values


class OpenIdAuth(BaseOpenIdAuth):
    AUTH_BACKEND = OpenIDBackend


BACKENDS = {
    'openid': OpenIdAuth
}
