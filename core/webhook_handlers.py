import stripe
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.models import Profile, SubscriptionPlan


def update_mode(user, event):
    if event["data"]["object"]["status"] == "trialing":
        user.profile.subscription_mode = Profile.TRIAL
    elif event["data"]["object"]["status"] == "active":
        user.profile.subscription_mode = Profile.FULL
    else:
        user.profile.subscription_mode = None

def _process_subscription_event(event):
    user = get_object_or_404(
        Profile, customer_id=event["data"]["object"]["customer"]
    ).user
    subscription_object = event["data"]["object"]["items"]["data"][-1]
    # Upserting plan
    plan_id = subscription_object["price"]["product"]
    stripe_plan = stripe.Product.retrieve(plan_id)
    SubscriptionPlan.update_plan(stripe_plan)

    # Updating user
    user.profile.subscription_expiry = timezone.datetime.fromtimestamp(
        event["data"]["object"]["current_period_end"]
    )

    user.profile.subscription_plan = get_object_or_404(SubscriptionPlan, pk=plan_id)

    if event["type"] != "customer.subscription.deleted":
        user.profile.subscription_id = event["data"]["object"]["id"]
    
    update_mode(user, event)

    user.save()


def _update_product(event):
    # Updating plan
    plan = event["data"]["object"]
    SubscriptionPlan.update_plan(plan)
