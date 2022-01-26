from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.utils import get_subscription_status


class Profile(models.Model):
    FULL = "FULL"
    TRIAL = "TRIAL"
    SUBSCRIPTION_CHOICES = [
        (None, _("No subscription")),
        (FULL, _("Full")),
        (TRIAL, _("Trial")),
    ]
    subscription_mode = models.CharField(
        max_length=5, choices=SUBSCRIPTION_CHOICES, default=None, null=True
    )
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    subscription_plan = models.ForeignKey(
        "SubscriptionPlan", on_delete=models.SET_NULL, null=True, blank=True
    )
    subscription_expiry = models.DateTimeField(null=True, blank=True)
    customer_id = models.CharField(max_length=50, null=True, blank=True)
    subscription_id = models.CharField(max_length=50, null=True, blank=True)

    @property
    def stripe_subscription_mode(self):
        status = get_subscription_status(self.user)
        trial_mode = (
            status == "trialing"
            and timezone.now() > self.user.profile.subscription_expiry
        )
        active = (
            status == "active"
            and timezone.now() > self.user.profile.subscription_expiry
        )
        if trial_mode:
            return self.TRIAL
        elif active:
            return self.FULL
        else:
            return None

    @property
    def is_subscribed(self):
        return (
            self.subscription_expiry is not None
            and self.subscription_expiry > timezone.now()
        )

    def __str__(self):
        return self.user.username


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()


class SubscriptionPlan(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=30)

    @staticmethod
    def update_plan(new_plan):
        plan = SubscriptionPlan.objects.get_or_create(id=new_plan["id"])[0]
        plan.name = new_plan["name"]
        plan.save()

    def __str__(self):
        return self.name


class StripeEvent(models.Model):
    id = models.CharField(max_length=100, primary_key=True)

    def __str__(self):
        return self.id
