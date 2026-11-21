"""Expire subscriptions, ad campaigns and promotions whose end dates have passed.

Run daily via cron / scheduled task / Celery beat:
    python manage.py expire_stale
"""

from datetime import timedelta

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from myapp.models import AdvertisementCampaign, Promotion, SubscriptionRequest
from myapp.notifications import notify_user


class Command(BaseCommand):
    help = "Flip expired subscriptions, ad campaigns and promotions to their final statuses and notify owners."

    def handle(self, *args, **options):
        now = timezone.now()
        today = timezone.localdate()
        totals = {"subscriptions": 0, "campaigns": 0, "promotions": 0}

        # 1. Subscriptions that have passed their ends_at
        expired_subscriptions = SubscriptionRequest.objects.filter(
            status=SubscriptionRequest.ACTIVE, ends_at__isnull=False, ends_at__lt=now
        ).select_related("business", "plan")

        for subscription in expired_subscriptions:
            subscription.status = SubscriptionRequest.EXPIRED
            subscription.save(update_fields=("status",))
            totals["subscriptions"] += 1
            if subscription.business.owner:
                notify_user(
                    subscription.business.owner,
                    f"Your '{subscription.plan.name}' subscription for {subscription.business.name} has expired.",
                    url="/dashboard/",
                    email_subject="Subscription expired",
                )

        # 2. Ad campaigns past their end date
        expired_campaigns = AdvertisementCampaign.objects.filter(
            status=AdvertisementCampaign.ACTIVE, ends_on__isnull=False, ends_on__lt=today
        ).select_related("business")

        for campaign in expired_campaigns:
            campaign.status = AdvertisementCampaign.COMPLETED
            campaign.save(update_fields=("status",))
            totals["campaigns"] += 1
            if campaign.business.owner:
                notify_user(
                    campaign.business.owner,
                    f"Your advertisement '{campaign.title}' has completed its run.",
                    url="/dashboard/",
                    email_subject="Advertisement completed",
                )

        # 3. Promotions that ended more than a day ago (they self-hide via
        #    Promotion.is_current, so this just tidies up)
        stale_promotions = Promotion.objects.filter(
            is_published=True, ends_on__isnull=False, ends_on__lt=today - timedelta(days=1)
        )
        totals["promotions"] = stale_promotions.update(is_published=False)

        # Homepage/directory caches now show stale data after expiry — clear them.
        cache.clear()

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {totals['subscriptions']} subscriptions, "
                f"{totals['campaigns']} campaigns, unpublished {totals['promotions']} promotions."
            )
        )
