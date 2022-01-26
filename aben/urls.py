from django.contrib import admin
from django.urls import include, path

from core.views import (cancel_subscription, customer_portal, dashboard, home,
                        logout_view, subscribe, webhook)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django_registration.backends.one_step.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", home, name="home"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
    path("subscribe/", subscribe, name="subscribe"),
    path("cancel-subscription/", cancel_subscription, name="cancel_subscription"),
    path("customer-portal/", customer_portal, name="customer_portal"),
    path("webhook", webhook, name="webhook"),
]
