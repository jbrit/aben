from django.contrib import admin

from core.models import Profile, StripeEvent, SubscriptionPlan

admin.site.register(Profile)
admin.site.register(StripeEvent)
admin.site.register(SubscriptionPlan)
