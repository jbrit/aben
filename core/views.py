import os

import stripe
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render, resolve_url
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.models import StripeEvent
from core.utils import (create_stripe_customer, get_subscription_plan,
                        start_stripe_subscription)
from core.webhook_handlers import _process_subscription_event, _update_product

stripe.api_key = os.environ.get("STRIPE_API_KEY")


def home(request):
    return render(request, "home.html")


def logout_view(request):
    logout(request)
    return redirect("/")


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def subscribe(request):
    current_user = request.user
    if not current_user.profile.customer_id:
        create_stripe_customer(current_user)

    if not current_user.profile.subscription_id:
        start_stripe_subscription(current_user)
    else:
        sub = stripe.Subscription.retrieve(current_user.profile.subscription_id)
        # Check if subscription is active
        if sub["status"] == "active":
            return HttpResponse("You are already subscribed.")
        # Check if subscription is in trial
        if sub["status"] == "trialing":
            return HttpResponse("You are already in trial.")

        # create checkout session
        session = stripe.checkout.Session.create(
            success_url=f"{settings.SITE_URL}/dashboard",
            cancel_url=f"{settings.SITE_URL}/dashboard",
            mode="subscription",
            payment_method_types=["card"],
            customer=current_user.profile.customer_id,
            line_items=[{"price": get_subscription_plan(), "quantity": 1}],
        )
        return redirect(session["url"])

    return redirect(resolve_url("dashboard"))


@login_required
def cancel_subscription(request):
    current_user = request.user
    if not current_user.profile.subscription_id:
        return HttpResponse("You are not subscribed.")

    sub = stripe.Subscription.retrieve(current_user.profile.subscription_id)
    if sub["status"] == "canceled":
        return HttpResponse("You are already unsubscribed.")

    # clear stripe and local subscription
    stripe.Subscription.delete(current_user.profile.subscription_id)
    current_user.profile.subscription_expiry = timezone.now()
    current_user.save()

    return redirect(resolve_url("dashboard"))


@login_required
def customer_portal(request):
    current_user = request.user
    if not current_user.profile.customer_id:
        create_stripe_customer(current_user)

    session = stripe.billing_portal.Session.create(
        customer=current_user.profile.customer_id,
        return_url=settings.SITE_URL,
    )
    return redirect(session.url)


@csrf_exempt
def webhook(request):
    webhooks = {
        "customer.subscription.created": _process_subscription_event,
        "customer.subscription.updated": _process_subscription_event,
        "customer.subscription.deleted": _process_subscription_event,
        "product.updated": _update_product,
    }
    webhook_secret = os.environ.get("WEBHOOK_SECRET")
    payload = request.body
    received_sig = request.META["HTTP_STRIPE_SIGNATURE"]

    try:
        event = stripe.Webhook.construct_event(payload, received_sig, webhook_secret)
    except ValueError:
        return HttpResponse("Bad Payload", status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse("Bad Signature", status=400)

    if event["type"] in webhooks:
        event_id = event["id"]
        try:
            StripeEvent.objects.get(event_id)
            return HttpResponse("Already Processed", status=400)
        except Exception:
            pass
        # handle webhook event
        webhooks[event["type"]](event)
        # save event as handled
        event = StripeEvent(id=event_id)
        event.save()
    return HttpResponse("Event processed", 200)
