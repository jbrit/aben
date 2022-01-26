import os
import stripe
from django.shortcuts import render, redirect, resolve_url
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.utils import timezone

from core.models import StripeEvent
from django.views.decorators.csrf import csrf_exempt

from core.utils import (
    create_stripe_customer,
    start_stripe_subscription,
    get_subscription_plan,
)
from core.webhook_handlers import _process_subscription_event, _update_product

stripe.api_key = os.environ.get("STRIPE_API_KEY")


def home(request):
    return render(request, "home.html")


def logout_view(request):
    logout(request)
    return redirect("/")


@login_required
def dashboard(request):
    context = dict()

    return render(request, "dashboard.html", context)


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
            success_url="http://localhost:8000/dashboard",
            cancel_url="http://localhost:8000/dashboard",
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
    print(sub)
    if sub["status"] == "canceled":
        return HttpResponse("You are already unsubscribed.")

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
        return_url=f"http://localhost:8000/",
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
        print("Error while decoding event!")
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
        webhooks[event["type"]](event)
        event = StripeEvent(id=event_id)
        event.save()
    return HttpResponse("Event processed", 200)
