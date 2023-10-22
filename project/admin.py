from django.contrib import admin
from django.contrib.auth.models import Group
from ninja_jwt.token_blacklist.models import OutstandingToken, BlacklistedToken

admin.site.unregister(Group)
admin.site.unregister(OutstandingToken)
admin.site.unregister(BlacklistedToken)
