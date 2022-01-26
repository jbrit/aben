import stripe
from django.http import HttpResponse


def get_subscription_plan():
    # filter stripe for all active plans
    products = stripe.Product.list(active=True)["data"]
    if products:
        product_id = products[0]["id"]
        # get the pricing plan for the first product
        price_id = stripe.Price.list(product=product_id)["data"][0]["id"]
        return price_id
    return None


def create_stripe_customer(current_user):
    # Create new customer object
    try:
        customer = stripe.Customer.create(
            email=current_user.email, metadata={"user_id": current_user.id}
        )
    except stripe.error.StripeError:
        return HttpResponse(
            "There was an error processing your payment method. Please try again.",
            status=500,
        )
    current_user.profile.customer_id = customer.id
    current_user.save()


def start_stripe_subscription(current_user):
    try:
        subscription = stripe.Subscription.create(
            customer=current_user.profile.customer_id,
            items=[
                {
                    "price": get_subscription_plan(),
                },
            ],
            trial_period_days=7,
        )
        current_user.profile.subscription_id = subscription["id"]
        current_user.save()
    except stripe.error.StripeError:
        return HttpResponse(
            "There was an error processing your subscription. Please try again.",
            status=500,
        )


def get_subscription_status(current_user):
    sub = stripe.Subscription.retrieve(current_user.profile.subscription_id)
    return sub["status"]
