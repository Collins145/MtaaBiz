from django.contrib import admin, messages
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from .models import (
    AdvertisementCampaign,
    Business,
    BusinessClaim,
    BusinessEvent,
    BusinessReport,
    BusinessReview,
    BusinessVerificationRequest,
    Category,
    ContentArticle,
    Contact,
    FavoriteBusiness,
    ListingPlan,
    ManualPayment,
    MarketplaceCategory,
    MarketplaceEnquiry,
    MarketplaceListing,
    NewsletterSubscription,
    Promotion,
    RecentlyViewedBusiness,
    ServiceBooking,
    SiteSettings,
    SubscriptionRequest,
    SocialLink,
    Testimonial,
    UserNotification,
    UserNotificationPreference,
)
from .notifications import notify_user
from .reviews import refresh_business_rating


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "display_order", "is_active")
    list_editable = ("display_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner",
        "category",
        "county",
        "town",
        "latitude",
        "longitude",
        "is_published",
        "is_featured",
        "is_popular",
        "is_verified",
    )
    list_filter = ("is_published", "is_featured", "is_popular", "is_verified", "category")
    list_editable = ("is_published", "is_featured", "is_popular", "is_verified")
    search_fields = (
        "name",
        "owner__username",
        "owner__email",
        "description",
        "offerings",
        "location",
        "county",
        "town",
        "physical_address",
        "email",
        "phone",
    )


@admin.register(MarketplaceCategory)
class MarketplaceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_editable = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(MarketplaceListing)
class MarketplaceListingAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "listing_type",
        "category",
        "business",
        "price",
        "is_available",
        "is_published",
    )
    list_filter = ("listing_type", "category", "is_available", "is_published")
    list_editable = ("is_available", "is_published")
    search_fields = ("name", "description", "business__name")


@admin.register(MarketplaceEnquiry)
class MarketplaceEnquiryAdmin(admin.ModelAdmin):
    list_display = ("listing", "customer", "customer_name", "email", "enquiry_type", "status", "created_at")
    list_filter = ("enquiry_type", "status", "created_at")
    list_editable = ("status",)
    search_fields = ("listing__name", "customer__username", "customer_name", "email", "phone", "message")
    readonly_fields = ("created_at",)


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "business", "starts_on", "ends_on", "is_published")
    list_filter = ("is_published", "starts_on", "ends_on")
    list_editable = ("is_published",)
    search_fields = ("title", "description", "business__name")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "rating", "is_published", "display_order")
    list_filter = ("is_published", "rating")
    list_editable = ("is_published", "display_order")
    search_fields = ("name", "role", "quote")


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("email", "subscribed_at")
    search_fields = ("email",)
    readonly_fields = ("email", "subscribed_at")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "url", "display_order", "is_active")
    list_editable = ("display_order", "is_active")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject")
    search_fields = ("name", "email", "subject")


@admin.register(BusinessVerificationRequest)
class BusinessVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("business", "contact_name", "email", "status", "submitted_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("business__name", "registration_number", "contact_name", "email")
    readonly_fields = ("submitted_at", "reviewed_at")
    actions = ("approve_verifications", "request_more_information")

    @admin.action(description="Approve selected verification requests")
    def approve_verifications(self, request, queryset):
        reviewed_at = timezone.now()
        with transaction.atomic():
            for verification in queryset.select_related("business"):
                verification.status = BusinessVerificationRequest.APPROVED
                verification.reviewed_at = reviewed_at
                verification.save(update_fields=("status", "reviewed_at"))
                verification.business.is_verified = True
                verification.business.save(update_fields=("is_verified",))
        self.message_user(request, "Selected businesses are verified.", messages.SUCCESS)

    @admin.action(description="Request more information")
    def request_more_information(self, request, queryset):
        reviewed_at = timezone.now()
        queryset.update(
            status=BusinessVerificationRequest.REJECTED,
            reviewed_at=reviewed_at,
        )
        self.message_user(request, "Selected requests were returned for more information.", messages.SUCCESS)


@admin.register(BusinessClaim)
class BusinessClaimAdmin(admin.ModelAdmin):
    list_display = ("business", "user", "email", "status", "submitted_at")
    list_filter = ("status", "submitted_at")
    search_fields = ("business__name", "user__username", "email", "phone")
    readonly_fields = ("submitted_at", "reviewed_at", "status")
    actions = ("approve_claims", "reject_claims")

    @admin.action(description="Approve selected business claims")
    def approve_claims(self, request, queryset):
        reviewed_at = timezone.now()
        approved = 0
        already_claimed = 0
        with transaction.atomic():
            for claim in queryset.select_related("business", "user"):
                if claim.status != BusinessClaim.PENDING:
                    continue
                owner_assigned = Business.objects.filter(
                    pk=claim.business_id,
                    owner__isnull=True,
                ).update(owner_id=claim.user_id)
                if not owner_assigned:
                    claim.status = BusinessClaim.REJECTED
                    already_claimed += 1
                else:
                    claim.status = BusinessClaim.APPROVED
                    approved += 1
                claim.reviewed_at = reviewed_at
                claim.save(update_fields=("status", "reviewed_at"))
        message = f"Approved {approved} claim(s)."
        if already_claimed:
            message += f" Rejected {already_claimed} because the business already has an owner."
        self.message_user(request, message, messages.SUCCESS)

    @admin.action(description="Reject selected business claims")
    def reject_claims(self, request, queryset):
        reviewed_at = timezone.now()
        queryset.filter(status=BusinessClaim.PENDING).update(
            status=BusinessClaim.REJECTED,
            reviewed_at=reviewed_at,
        )
        self.message_user(request, "Selected pending claims were rejected.", messages.SUCCESS)


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = ("listing", "customer", "appointment_at", "status", "created_at")
    list_filter = ("status", "appointment_at", "created_at")
    search_fields = ("listing__name", "customer__username", "customer__email", "message")
    readonly_fields = ("created_at", "updated_at")


@admin.register(BusinessReview)
class BusinessReviewAdmin(admin.ModelAdmin):
    list_display = ("business", "customer", "rating", "title", "is_approved", "created_at")
    list_filter = ("is_approved", "rating", "created_at")
    search_fields = ("business__name", "customer__username", "title", "body")
    readonly_fields = ("is_approved", "created_at", "updated_at")
    actions = ("approve_reviews", "reject_reviews")

    @admin.action(description="Approve selected reviews")
    def approve_reviews(self, request, queryset):
        reviews = list(queryset.select_related("business", "customer"))
        business_ids = {review.business_id for review in reviews}
        with transaction.atomic():
            queryset.update(is_approved=True)
            for business_id in business_ids:
                refresh_business_rating(business_id)
            for review in reviews:
                notify_user(
                    review.customer,
                    message=f"Your review for {review.business.name} is now published.",
                    url=reverse("customer_dashboard"),
                )
        self.message_user(request, "Selected reviews were approved.", messages.SUCCESS)

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        business_ids = set(queryset.values_list("business_id", flat=True))
        with transaction.atomic():
            queryset.update(is_approved=False)
            for business_id in business_ids:
                refresh_business_rating(business_id)
        self.message_user(request, "Selected reviews were rejected.", messages.SUCCESS)


@admin.register(BusinessEvent)
class BusinessEventAdmin(admin.ModelAdmin):
    list_display = ("business", "event_type", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("business__name",)
    readonly_fields = ("business", "event_type", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ContentArticle)
class ContentArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "content_type", "author", "is_published", "published_at")
    list_filter = ("content_type", "is_published", "published_at")
    list_editable = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "summary", "body", "author")
    date_hierarchy = "published_at"


@admin.register(ListingPlan)
class ListingPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "amount", "billing_period", "is_active", "display_order")
    list_editable = ("amount", "billing_period", "is_active", "display_order")
    search_fields = ("name", "description")


@admin.register(SubscriptionRequest)
class SubscriptionRequestAdmin(admin.ModelAdmin):
    list_display = ("business", "plan", "status", "amount_due", "created_at", "ends_at")
    list_filter = ("status", "plan", "created_at")
    list_editable = ("status",)
    search_fields = ("business__name", "plan__name")
    readonly_fields = ("created_at",)


@admin.register(AdvertisementCampaign)
class AdvertisementCampaignAdmin(admin.ModelAdmin):
    list_display = ("title", "business", "placement", "status", "amount_due", "starts_on", "ends_on")
    list_filter = ("placement", "status", "starts_on", "ends_on")
    list_editable = ("status", "amount_due")
    search_fields = ("title", "business__name", "notes")
    readonly_fields = ("created_at",)


@admin.register(ManualPayment)
class ManualPaymentAdmin(admin.ModelAdmin):
    list_display = ("business", "amount", "method", "reference", "status", "submitted_at")
    list_filter = ("status", "method", "submitted_at")
    search_fields = ("business__name", "reference")
    readonly_fields = ("business", "subscription", "campaign", "amount", "method", "reference", "status", "submitted_at", "reviewed_at")
    actions = ("confirm_payments", "reject_payments")

    @admin.action(description="Confirm selected manual payments")
    def confirm_payments(self, request, queryset):
        reviewed_at = timezone.now()
        confirmed = 0
        mismatched = 0
        with transaction.atomic():
            for payment in queryset.select_related("subscription", "campaign"):
                if payment.status != ManualPayment.SUBMITTED:
                    continue
                target = payment.subscription or payment.campaign
                expected_amount = target.amount_due
                target_status = target.status
                if (
                    expected_amount is None
                    or payment.amount != expected_amount
                    or target_status not in (
                        SubscriptionRequest.AWAITING_PAYMENT,
                        AdvertisementCampaign.AWAITING_PAYMENT,
                    )
                ):
                    mismatched += 1
                    continue
                payment.status = ManualPayment.CONFIRMED
                payment.reviewed_at = reviewed_at
                payment.save(update_fields=("status", "reviewed_at"))
                if payment.subscription_id:
                    payment.subscription.status = SubscriptionRequest.ACTIVE
                    payment.subscription.save(update_fields=("status",))
                if payment.campaign_id:
                    payment.campaign.status = AdvertisementCampaign.ACTIVE
                    payment.campaign.save(update_fields=("status",))
                _owner = payment.business.owner
                if _owner:
                    notify_user(
                        _owner,
                        message=f"Manual payment for {payment.business.name} was confirmed.",
                        url=reverse("business_dashboard"),
                    )
                confirmed += 1
        level = messages.WARNING if mismatched else messages.SUCCESS
        message = f"Confirmed {confirmed} payment(s)."
        if mismatched:
            message += f" {mismatched} payment(s) were not confirmed because the amount does not match the request."
        self.message_user(request, message, level)

    @admin.action(description="Reject selected manual payments")
    def reject_payments(self, request, queryset):
        payments = list(queryset.filter(status=ManualPayment.SUBMITTED).select_related("business"))
        with transaction.atomic():
            queryset.filter(status=ManualPayment.SUBMITTED).update(
                status=ManualPayment.REJECTED,
                reviewed_at=timezone.now(),
            )
            for payment in payments:
                if payment.business.owner:
                    notify_user(
                        payment.business.owner,
                        message=f"Manual payment for {payment.business.name} was not confirmed. Contact MtaaBiz for help.",
                        url=reverse("business_dashboard"),
                    )
        self.message_user(request, "Selected payments were rejected.", messages.SUCCESS)


@admin.register(FavoriteBusiness)
class FavoriteBusinessAdmin(admin.ModelAdmin):
    list_display = ("user", "business", "created_at")
    search_fields = ("user__username", "business__name")
    readonly_fields = ("user", "business", "created_at")


@admin.register(RecentlyViewedBusiness)
class RecentlyViewedBusinessAdmin(admin.ModelAdmin):
    list_display = ("user", "business", "last_viewed_at")
    search_fields = ("user__username", "business__name")
    readonly_fields = ("user", "business", "last_viewed_at")


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "message")
    readonly_fields = ("created_at",)


@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "in_app_enabled")
    list_editable = ("in_app_enabled",)
    search_fields = ("user__username", "user__email")


@admin.register(BusinessReport)
class BusinessReportAdmin(admin.ModelAdmin):
    list_display = ("business", "reason", "reporter", "status", "created_at")
    list_filter = ("reason", "status", "created_at")
    list_editable = ("status",)
    search_fields = ("business__name", "reporter__username", "details", "admin_notes")
    readonly_fields = ("business", "reporter", "reason", "details", "created_at")

    def save_model(self, request, obj, form, change):
        if obj.status != BusinessReport.PENDING and obj.reviewed_at is None:
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = (
        "support_email",
        "support_phone",
        "whatsapp_phone",
        "contact_address",
        "mission",
        "vision",
        "updated_at",
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False