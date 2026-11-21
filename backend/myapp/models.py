import json
import re

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .validators import ImageUploadValidator

business_image_validator = ImageUploadValidator()

# Create your models here.
class Contact(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    subject = models.CharField(max_length=50)
    message = models.TextField()

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    icon_class = models.CharField(max_length=80, default="bi bi-grid")
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Business(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=150, unique=True, blank=True, allow_unicode=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="businesses",
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="businesses"
    )
    description = models.TextField(blank=True)
    offerings = models.TextField(
        blank=True, help_text="Products and services offered; these are included in search."
    )
    county = models.CharField(max_length=100, blank=True)
    town = models.CharField(max_length=120, blank=True)
    physical_address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=(MinValueValidator(-90), MaxValueValidator(90)),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=(MinValueValidator(-180), MaxValueValidator(180)),
    )
    opening_hours = models.TextField(
        blank=True,
        help_text=(
            "Structured weekly hours as JSON, e.g. {\"mon\": \"08:00-17:00\", ...}. "
            "Free-text hours go into description instead."
        ),
    )
    location = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    logo_url = models.URLField(max_length=500, blank=True)
    cover_image_url = models.URLField(max_length=500, blank=True)
    image = models.ImageField(
        upload_to="business/images/", blank=True, null=True, validators=(business_image_validator,)
    )
    logo = models.ImageField(
        upload_to="business/logos/", blank=True, null=True, validators=(business_image_validator,)
    )
    cover_image = models.ImageField(
        upload_to="business/covers/", blank=True, null=True, validators=(business_image_validator,)
    )
    contact_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    website_url = models.URLField(max_length=500, blank=True)
    facebook_url = models.URLField(max_length=500, blank=True)
    instagram_url = models.URLField(max_length=500, blank=True)
    tiktok_url = models.URLField(max_length=500, blank=True)
    x_url = models.URLField(max_length=500, blank=True)
    linkedin_url = models.URLField(max_length=500, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    review_count = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-is_featured", "-rating", "name")
        indexes = [
            models.Index(fields=("is_published", "is_featured")),
            models.Index(fields=("is_published", "category")),
            models.Index(fields=("is_published", "county")),
            models.Index(fields=("is_published", "town")),
            models.Index(fields=("is_published", "-rating")),
            models.Index(fields=("slug",)),
            models.Index(fields=("-created_at",)),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:140] or "business"
            slug = base
            counter = 2
            while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("business_detail_by_slug", args=[self.pk, self.slug])

    @property
    def opening_hours_dict(self):
        """Parse the structured opening-hours JSON into a dict keyed by weekday."""
        raw = (self.opening_hours or "").strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return {str(k).lower()[:3]: str(v) for k, v in data.items() if v}
        except (ValueError, TypeError):
            return {}

    @property
    def is_open_now(self):
        """Best-effort check of today's hours, e.g. '08:00-17:00' or 'open' / 'closed'."""
        hours = self.opening_hours_dict
        today = timezone.localdate().strftime("%a").lower()[:3]
        entry = hours.get(today)
        if not entry:
            return None
        entry = entry.strip().lower()
        if entry in ("closed", "no"):
            return False
        if entry in ("open", "24h", "24/7"):
            return True
        match = re.match(r"^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$", entry)
        if not match:
            return None
        now = timezone.localtime().time()
        import datetime as _dt

        start = _dt.time(int(match.group(1)), int(match.group(2)))
        end = _dt.time(int(match.group(3)), int(match.group(4)))
        return start <= now <= end

    @property
    def formatted_location(self):
        location_parts = (
            self.physical_address,
            self.town,
            self.county,
        )
        formatted = ", ".join(part.strip() for part in location_parts if part and part.strip())
        return formatted or self.location


class BusinessVerificationRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (PENDING, "Pending review"),
        (APPROVED, "Approved"),
        (REJECTED, "More information required"),
    )

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="verification_requests"
    )
    registration_number = models.CharField(max_length=100, blank=True)
    contact_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"Verification request for {self.business.name}"


class BusinessClaim(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (PENDING, "Pending review"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    )

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="claims"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_claims"
    )
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("business", "user"),
                condition=models.Q(status="pending"),
                name="unique_pending_business_claim",
            )
        ]

    def __str__(self):
        return f"{self.user} claims {self.business.name}"


class MarketplaceCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "marketplace categories"

    def __str__(self):
        return self.name


class MarketplaceListing(models.Model):
    PRODUCT = "product"
    SERVICE = "service"
    LISTING_TYPE_CHOICES = (
        (PRODUCT, "Product"),
        (SERVICE, "Service"),
    )

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="marketplace_listings"
    )
    category = models.ForeignKey(
        MarketplaceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings",
    )
    listing_type = models.CharField(
        max_length=10, choices=LISTING_TYPE_CHOICES, default=PRODUCT
    )
    name = models.CharField(max_length=160)
    description = models.TextField()
    image_url = models.URLField(max_length=500, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "name")

    def __str__(self):
        return self.name


class MarketplaceEnquiry(models.Model):
    ENQUIRY = "enquiry"
    ORDER_REQUEST = "order_request"
    QUOTE_REQUEST = "quote_request"
    ENQUIRY_TYPE_CHOICES = (
        (ENQUIRY, "General enquiry"),
        (ORDER_REQUEST, "Order request"),
        (QUOTE_REQUEST, "Request a quote"),
    )
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"
    STATUS_CHOICES = (
        (NEW, "New"),
        (CONTACTED, "Contacted"),
        (CLOSED, "Closed"),
    )

    listing = models.ForeignKey(
        MarketplaceListing, on_delete=models.CASCADE, related_name="enquiries"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marketplace_enquiries",
    )
    customer_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    enquiry_type = models.CharField(
        max_length=20, choices=ENQUIRY_TYPE_CHOICES, default=ENQUIRY
    )
    message = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=NEW)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_enquiry_type_display()} for {self.listing}"


class Promotion(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="promotions"
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-starts_on", "-created_at")

    def __str__(self):
        return self.title

    @property
    def is_current(self):
        today = timezone.localdate()
        return (
            self.is_published
            and self.business.is_published
            and (self.starts_on is None or self.starts_on <= today)
            and (self.ends_on is None or self.ends_on >= today)
        )


class Testimonial(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    photo_url = models.URLField(max_length=500, blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    is_published = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class SocialLink(models.Model):
    platform = models.CharField(max_length=40)
    url = models.URLField(max_length=500)
    icon_class = models.CharField(max_length=80)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("display_order", "platform")

    def __str__(self):
        return self.platform


class FavoriteBusiness(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorite_businesses"
    )
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="favorited_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "business"), name="unique_business_favorite")
        ]

    def __str__(self):
        return f"{self.user} saved {self.business.name}"


class RecentlyViewedBusiness(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recently_viewed_businesses"
    )
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="recently_viewed_by"
    )
    last_viewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-last_viewed_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "business"), name="unique_recently_viewed_business"
            )
        ]


class UserNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.message


class ServiceBooking(models.Model):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (DECLINED, "Declined"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    )

    listing = models.ForeignKey(
        MarketplaceListing, on_delete=models.CASCADE, related_name="bookings"
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_bookings"
    )
    appointment_at = models.DateTimeField()
    message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("appointment_at", "-created_at")

    def __str__(self):
        return f"Booking for {self.listing.name} by {self.customer}"


class BusinessReview(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_reviews"
    )
    rating = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(5))
    )
    title = models.CharField(max_length=120)
    body = models.TextField()
    owner_response = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("business", "is_approved", "-created_at"))]
        constraints = [
            models.UniqueConstraint(fields=("business", "customer"), name="unique_customer_business_review")
        ]

    def __str__(self):
        return f"{self.rating}/5 review for {self.business.name}"


class UserLoginEvent(models.Model):
    METHOD_PASSWORD = "password"
    METHOD_GOOGLE = "google"
    METHOD_CHOICES = (
        (METHOD_PASSWORD, "Username / password"),
        (METHOD_GOOGLE, "Google sign-in"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_events",
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default=METHOD_PASSWORD)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        indexes = [models.Index(fields=("user", "-created_at"))]

    def __str__(self):
        return f"{self.user} · {self.get_method_display()} · {self.created_at}"


class BusinessEvent(models.Model):
    PROFILE_VIEW = "profile_view"
    PHONE_CLICK = "phone_click"
    EMAIL_CLICK = "email_click"
    WHATSAPP_CLICK = "whatsapp_click"
    WEBSITE_CLICK = "website_click"
    EVENT_CHOICES = (
        (PROFILE_VIEW, "Profile view"),
        (PHONE_CLICK, "Phone click"),
        (EMAIL_CLICK, "Email click"),
        (WHATSAPP_CLICK, "WhatsApp click"),
        (WEBSITE_CLICK, "Website click"),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("business", "event_type", "created_at"))]

    def __str__(self):
        return f"{self.get_event_type_display()} · {self.business.name}"


class BusinessFinderSearch(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="business_finder_searches",
    )
    query = models.CharField(max_length=500)
    result_business_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        indexes = [models.Index(fields=("user", "-created_at"))]
        verbose_name = "business finder search"
        verbose_name_plural = "business finder searches"

    def __str__(self):
        return f"{self.user}: {self.query}"


class ContentArticle(models.Model):
    BLOG = "blog"
    RESOURCE = "resource"
    CONTENT_TYPES = ((BLOG, "Blog article"), (RESOURCE, "Business Hub resource"))

    content_type = models.CharField(max_length=10, choices=CONTENT_TYPES, default=BLOG)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=190, unique=True)
    summary = models.CharField(max_length=300)
    body = models.TextField()
    image_url = models.URLField(max_length=500, blank=True)
    author = models.CharField(max_length=120, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    meta_description = models.CharField(
        max_length=300, blank=True, help_text="SEO meta description; falls back to summary."
    )

    class Meta:
        ordering = ("-published_at", "-created_at")
        indexes = [
            models.Index(fields=("content_type", "is_published")),
            models.Index(fields=("slug",)),
        ]

    def __str__(self):
        return self.title


class ListingPlan(models.Model):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    BILLING_CHOICES = (
        (ONE_TIME, "One time"),
        (MONTHLY, "Monthly"),
        (YEARLY, "Yearly"),
    )

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    billing_period = models.CharField(max_length=10, choices=BILLING_CHOICES, default=MONTHLY)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name


class SubscriptionRequest(models.Model):
    REQUESTED = "requested"
    AWAITING_PAYMENT = "awaiting_payment"
    ACTIVE = "active"
    REJECTED = "rejected"
    EXPIRED = "expired"
    STATUS_CHOICES = (
        (REQUESTED, "Request received"),
        (AWAITING_PAYMENT, "Awaiting manual payment"),
        (ACTIVE, "Active"),
        (REJECTED, "Not approved"),
        (EXPIRED, "Expired"),
    )

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="subscription_requests"
    )
    plan = models.ForeignKey(ListingPlan, on_delete=models.PROTECT, related_name="requests")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=REQUESTED)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.business.name} · {self.plan.name}"


class AdvertisementCampaign(models.Model):
    HOMEPAGE = "homepage"
    DIRECTORY = "directory"
    CATEGORY = "category"
    PLACEMENT_CHOICES = (
        (HOMEPAGE, "Homepage"),
        (DIRECTORY, "Business directory"),
        (CATEGORY, "Category results"),
    )
    PENDING = "pending"
    AWAITING_PAYMENT = "awaiting_payment"
    ACTIVE = "active"
    REJECTED = "rejected"
    COMPLETED = "completed"
    STATUS_CHOICES = (
        (PENDING, "Pending review"),
        (AWAITING_PAYMENT, "Awaiting manual payment"),
        (ACTIVE, "Active"),
        (REJECTED, "Not approved"),
        (COMPLETED, "Completed"),
    )

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name="advertisement_campaigns"
    )
    title = models.CharField(max_length=120)
    placement = models.CharField(max_length=12, choices=PLACEMENT_CHOICES)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status", "-created_at")),
            models.Index(fields=("placement", "status")),
            models.Index(fields=("starts_on", "ends_on")),
        ]

    def __str__(self):
        return f"{self.title} · {self.business.name}"


class ManualPayment(models.Model):
    MPESA = "mpesa"
    BANK = "bank"
    OTHER = "other"
    METHOD_CHOICES = ((MPESA, "M-Pesa"), (BANK, "Bank transfer"), (OTHER, "Other"))
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    STATUS_CHOICES = (
        (SUBMITTED, "Awaiting admin confirmation"),
        (CONFIRMED, "Confirmed"),
        (REJECTED, "Not confirmed"),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="manual_payments")
    subscription = models.ForeignKey(
        SubscriptionRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payments",
    )
    campaign = models.ForeignKey(
        AdvertisementCampaign,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=8, choices=METHOD_CHOICES)
    reference = models.CharField(max_length=120)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=SUBMITTED)
    admin_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-submitted_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(subscription__isnull=False, campaign__isnull=True)
                    | models.Q(subscription__isnull=True, campaign__isnull=False)
                ),
                name="manual_payment_has_single_target",
            ),
            models.UniqueConstraint(fields=("reference",), name="unique_manual_payment_reference"),
        ]

    def __str__(self):
        return f"{self.business.name} · {self.amount} · {self.reference}"


class UserNotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    in_app_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification preferences for {self.user}"


class BusinessReport(models.Model):
    WRONG_INFORMATION = "wrong_information"
    DUPLICATE = "duplicate"
    INAPPROPRIATE = "inappropriate"
    SUSPECTED_FRAUD = "suspected_fraud"
    OTHER = "other"
    REASON_CHOICES = (
        (WRONG_INFORMATION, "Incorrect information"),
        (DUPLICATE, "Duplicate listing"),
        (INAPPROPRIATE, "Inappropriate content"),
        (SUSPECTED_FRAUD, "Suspected fraud or impersonation"),
        (OTHER, "Other"),
    )
    PENDING = "pending"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"
    STATUS_CHOICES = (
        (PENDING, "Pending review"),
        (REVIEWED, "Reviewed"),
        (DISMISSED, "Dismissed"),
    )

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="business_reports",
    )
    reason = models.CharField(max_length=24, choices=REASON_CHOICES)
    details = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.get_reason_display()} report for {self.business.name}"


class SiteSettings(models.Model):
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=30, blank=True)
    whatsapp_phone = models.CharField(max_length=30, blank=True)
    contact_address = models.CharField(max_length=255, blank=True)
    mission = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def whatsapp_url(self):
        digits = "".join(character for character in self.whatsapp_phone if character.isdigit())
        if digits.startswith("0"):
            digits = f"254{digits[1:]}"
        elif len(digits) == 9:
            digits = f"254{digits}"
        return f"https://wa.me/{digits}" if digits else ""

    def __str__(self):
        return "MtaaBiz contact and site settings"
# Use the str(string) method to return the name of the contact when you query the database. This will make it easier to identify contacts in the Django admin interface and other parts of your application.
