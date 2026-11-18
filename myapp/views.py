import csv
import math
import re
from datetime import timedelta

from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordForm,
)
from django.contrib.auth import update_session_auth_hash
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Exists, F, OuterRef, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    AdvertisementCampaignForm,
    AccountRegistrationForm,
    BookingStatusForm,
    BusinessReviewForm,
    BusinessReviewResponseForm,
    BusinessSubmissionForm,
    BusinessClaimForm,
    BusinessVerificationForm,
    ContactForm,
    BusinessReportForm,
    EnquiryStatusForm,
    MarketplaceEnquiryForm,
    MarketplaceFilterForm,
    MarketplaceListingForm,
    ManualPaymentSubmissionForm,
    NewsletterForm,
    OwnerAccountForm,
    OwnerPromotionForm,
    NotificationPreferenceForm,
    ServiceBookingForm,
)
from .models import (
    AdvertisementCampaign,
    Business,
    BusinessClaim,
    BusinessEvent,
    BusinessFinderSearch,
    BusinessReport,
    BusinessReview,
    BusinessVerificationRequest,
    Category,
    ContentArticle,
    Contact,
    FavoriteBusiness,
    ListingPlan,
    ManualPayment,
    MarketplaceEnquiry,
    MarketplaceListing,
    NewsletterSubscription,
    Promotion,
    RecentlyViewedBusiness,
    ServiceBooking,
    SiteSettings,
    SocialLink,
    SubscriptionRequest,
    Testimonial,
    UserLoginEvent,
    UserNotification,
    UserNotificationPreference,
)
from .notifications import notify_user
from .reviews import refresh_business_rating

# Create your views here.

def error(request):
    return render(request, '404.html', status=404)

def details(request):
    return render(request, 'blog-details.html')

def blog(request):
    articles = ContentArticle.objects.filter(
        content_type=ContentArticle.BLOG, is_published=True
    )
    return render(request, "business_blog.html", {"articles": articles})


def business_hub(request):
    resources = ContentArticle.objects.filter(
        content_type=ContentArticle.RESOURCE, is_published=True
    )
    return render(request, "business_hub.html", {"resources": resources})


def article_detail(request, slug):
    article = get_object_or_404(
        ContentArticle,
        slug=slug,
        content_type=ContentArticle.BLOG,
        is_published=True,
    )
    return render(request, "article_detail.html", {"article": article})


def resource_detail(request, slug):
    article = get_object_or_404(
        ContentArticle,
        slug=slug,
        content_type=ContentArticle.RESOURCE,
        is_published=True,
    )
    return render(request, "article_detail.html", {"article": article})

def portfolio(request):
    return render(request, 'portfolio-details.html')

def service(request):
    return render(request, 'service-details.html')

def starter(request):
    return render(request, 'starter-page.html')

def _home_context():
    categories = Category.objects.filter(is_active=True)
    today = timezone.localdate()
    active_home_campaigns = AdvertisementCampaign.objects.filter(
        business=OuterRef("pk"),
        placement=AdvertisementCampaign.HOMEPAGE,
        status=AdvertisementCampaign.ACTIVE,
    ).filter(
        Q(starts_on__isnull=True) | Q(starts_on__lte=today),
        Q(ends_on__isnull=True) | Q(ends_on__gte=today),
    )

    return {
        "categories": categories,
        "hero_categories": categories[:7],
        "more_categories": categories[7:],
        "featured_businesses": Business.objects.filter(is_published=True)
        .annotate(is_sponsored=Exists(active_home_campaigns))
        .filter(Q(is_featured=True) | Q(is_sponsored=True))
        .select_related("category")
        .order_by("-is_sponsored", "-is_featured", "-rating", "name")[:4],
        "popular_businesses": Business.objects.filter(
            is_published=True, is_popular=True
        ).select_related("category")[:4],
        "promotions": _current_promotions()[:3],
        "testimonials": Testimonial.objects.filter(is_published=True)[:8],
    }


def index(request):
    return render(request, "index.html", _home_context())


def about(request):
    return render(
        request,
        "about.html",
        {"site_settings": SiteSettings.objects.first()},
    )


def _current_promotions():
    today = timezone.localdate()
    return Promotion.objects.filter(
        is_published=True,
        business__is_published=True,
    ).filter(
        Q(starts_on__isnull=True) | Q(starts_on__lte=today),
        Q(ends_on__isnull=True) | Q(ends_on__gte=today),
    ).select_related("business", "business__category")


def deals(request):
    return render(request, "deals.html", {"promotions": _current_promotions()})


def businesses(request):
    results = Business.objects.filter(is_published=True).select_related("category")
    today = timezone.localdate()
    active_directory_campaigns = AdvertisementCampaign.objects.filter(
        business=OuterRef("pk"),
        placement__in=(AdvertisementCampaign.DIRECTORY, AdvertisementCampaign.CATEGORY),
        status=AdvertisementCampaign.ACTIVE,
    ).filter(
        Q(starts_on__isnull=True) | Q(starts_on__lte=today),
        Q(ends_on__isnull=True) | Q(ends_on__gte=today),
    )
    query = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    location = request.GET.get("location", "").strip()

    if query:
        results = results.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(offerings__icontains=query)
            | Q(category__name__icontains=query)
        )
    if category_slug:
        results = results.filter(category__slug=category_slug)
    if location:
        results = results.filter(
            Q(location__icontains=location)
            | Q(county__icontains=location)
            | Q(town__icontains=location)
            | Q(physical_address__icontains=location)
        )

    results = results.annotate(is_sponsored=Exists(active_directory_campaigns)).order_by(
        "-is_sponsored", "-is_featured", "-rating", "name"
    )
    return render(
        request,
        "businesses.html",
        {
            "businesses": results,
            "categories": Category.objects.filter(is_active=True),
            "query": query,
            "selected_category": category_slug,
            "location": location,
        },
    )


def featured_businesses(request):
    today = timezone.localdate()
    active_campaigns = AdvertisementCampaign.objects.filter(
        business=OuterRef("pk"),
        placement__in=(AdvertisementCampaign.HOMEPAGE, AdvertisementCampaign.DIRECTORY),
        status=AdvertisementCampaign.ACTIVE,
    ).filter(
        Q(starts_on__isnull=True) | Q(starts_on__lte=today),
        Q(ends_on__isnull=True) | Q(ends_on__gte=today),
    )
    results = (
        Business.objects.filter(is_published=True)
        .annotate(is_sponsored=Exists(active_campaigns))
        .filter(Q(is_featured=True) | Q(is_sponsored=True))
        .select_related("category")
        .order_by("-is_sponsored", "-is_featured", "-rating", "name")
    )
    return render(
        request,
        "featured_businesses.html",
        {"businesses": results},
    )


def nearby_businesses(request):
    results = Business.objects.filter(
        is_published=True, latitude__isnull=False, longitude__isnull=False
    ).select_related("category")
    error = ""
    center = None
    radius = 25.0
    lat_value = request.GET.get("lat", "").strip()
    lng_value = request.GET.get("lng", "").strip()
    radius_value = request.GET.get("radius", "25").strip()

    if lat_value or lng_value:
        try:
            latitude = float(lat_value)
            longitude = float(lng_value)
            radius = float(radius_value)
            if (
                not math.isfinite(latitude)
                or not math.isfinite(longitude)
                or not math.isfinite(radius)
                or not -90 <= latitude <= 90
                or not -180 <= longitude <= 180
                or not 1 <= radius <= 100
            ):
                raise ValueError
            center = (latitude, longitude)
        except ValueError:
            error = "Enter valid map coordinates and a search radius from 1 to 100 km."
            return render(
                request,
                "nearby_businesses.html",
                {"businesses": (), "error": error, "radius": radius_value},
                status=400,
            )

    if center:
        latitude, longitude = center
        lat_delta = radius / 110.574
        lon_delta = radius / max(111.320 * math.cos(math.radians(latitude)), 0.01)
        results = results.filter(
            latitude__gte=latitude - lat_delta,
            latitude__lte=latitude + lat_delta,
            longitude__gte=longitude - lon_delta,
            longitude__lte=longitude + lon_delta,
        )
        nearby = []
        for business in results:
            lat1 = math.radians(latitude)
            lat2 = math.radians(float(business.latitude))
            dlat = lat2 - lat1
            dlon = math.radians(float(business.longitude) - longitude)
            haversine = (
                math.sin(dlat / 2) ** 2
                + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
            )
            business.distance_km = 6371 * 2 * math.asin(math.sqrt(haversine))
            if business.distance_km <= radius:
                nearby.append(business)
        businesses = sorted(nearby, key=lambda business: business.distance_km)
    else:
        businesses = ()

    return render(
        request,
        "nearby_businesses.html",
        {
            "businesses": businesses,
            "error": error,
            "latitude": lat_value,
            "longitude": lng_value,
            "radius": radius,
            "has_location": center is not None,
        },
    )


def business_detail(request, business_id):
    business = get_object_or_404(
        Business.objects.select_related("category"),
        pk=business_id,
        is_published=True,
    )
    if not request.user.is_authenticated or business.owner_id != request.user.pk:
        BusinessEvent.objects.create(
            business=business,
            event_type=BusinessEvent.PROFILE_VIEW,
        )
    if request.user.is_authenticated:
        RecentlyViewedBusiness.objects.update_or_create(
            user=request.user,
            business=business,
            defaults={"last_viewed_at": timezone.now()},
        )
        recent_ids = list(
            RecentlyViewedBusiness.objects.filter(user=request.user)
            .order_by("-last_viewed_at")
            .values_list("pk", flat=True)[:20]
        )
        RecentlyViewedBusiness.objects.filter(user=request.user).exclude(
            pk__in=recent_ids
        ).delete()

    return render(
        request,
        "business_detail.html",
        {
            "business": business,
            "is_favorite": request.user.is_authenticated
            and FavoriteBusiness.objects.filter(user=request.user, business=business).exists(),
            "listings": business.marketplace_listings.filter(
                is_published=True, is_available=True
            ).select_related("category"),
            "promotions": _current_promotions().filter(business=business),
            "reviews": business.reviews.filter(is_approved=True).select_related("customer"),
            "review_form": BusinessReviewForm(
                instance=BusinessReview.objects.filter(
                    business=business, customer=request.user
                ).first()
            )
            if request.user.is_authenticated
            else BusinessReviewForm(),
            "report_form": BusinessReportForm(),
        },
    )


@login_required
@require_POST
def toggle_business_favorite(request, business_id):
    business = get_object_or_404(Business, pk=business_id, is_published=True)
    favorite, created = FavoriteBusiness.objects.get_or_create(
        user=request.user, business=business
    )
    if not created:
        favorite.delete()
    return redirect("business_detail", business_id=business.pk)


def track_business_contact(request, business_id, contact_type):
    business = get_object_or_404(Business, pk=business_id, is_published=True)
    phone_number = re.sub(r"[^0-9+]", "", business.phone or "")
    targets = {
        "phone": (BusinessEvent.PHONE_CLICK, f"tel:{phone_number}" if phone_number else ""),
        "email": (BusinessEvent.EMAIL_CLICK, f"mailto:{business.email}" if business.email else ""),
        "website": (BusinessEvent.WEBSITE_CLICK, business.website_url),
    }
    if contact_type == "whatsapp":
        digits = re.sub(r"\D", "", business.phone or "")
        if digits.startswith("0"):
            digits = f"254{digits[1:]}"
        elif len(digits) == 9:
            digits = f"254{digits}"
        targets["whatsapp"] = (
            BusinessEvent.WHATSAPP_CLICK,
            f"https://wa.me/{digits}" if digits else "",
        )
    event = targets.get(contact_type)
    if not event or not event[1]:
        raise Http404("This contact method is not available.")
    BusinessEvent.objects.create(business=business, event_type=event[0])
    response = HttpResponse(status=302)
    response["Location"] = event[1]
    return response


def business_assistant(request):
    query = request.GET.get("q", "").strip()
    query_error = (
        "Searches must be 500 characters or fewer."
        if len(query) > 500
        else ""
    )
    businesses = []
    if query and not query_error:
        stop_words = {"a", "an", "and", "can", "find", "for", "i", "in", "me", "near", "the", "to", "where"}
        tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", query.casefold())
            if len(token) > 1 and token not in stop_words
        ]
        for business in Business.objects.filter(is_published=True).select_related("category"):
            listings = " ".join(
                business.marketplace_listings.filter(
                    is_published=True, is_available=True
                ).values_list("name", flat=True)
            )
            fields = {
                "name": business.name.casefold(),
                "category": business.category.name.casefold() if business.category else "",
                "offerings": business.offerings.casefold(),
                "description": business.description.casefold(),
                "location": " ".join(
                    (business.county, business.town, business.location)
                ).casefold(),
                "listings": listings.casefold(),
            }
            score = 0
            for token in tokens:
                score += 4 if token in fields["name"] else 0
                score += 3 if token in fields["category"] else 0
                score += 3 if token in fields["offerings"] or token in fields["listings"] else 0
                score += 1 if token in fields["description"] else 0
                score += 2 if token in fields["location"] else 0
            if score:
                business.match_score = score
                businesses.append(business)
        businesses.sort(key=lambda business: (-business.match_score, business.name.casefold()))
        businesses = businesses[:10]

        if request.user.is_authenticated:
            BusinessFinderSearch.objects.create(
                user=request.user,
                query=query,
                result_business_ids=[business.pk for business in businesses],
            )

    history_page_obj = None
    if request.user.is_authenticated:
        history_page_obj = Paginator(
            BusinessFinderSearch.objects.filter(user=request.user), 10
        ).get_page(request.GET.get("history_page"))
        history_entries = list(history_page_obj.object_list)
        saved_business_ids = {
            business_id
            for entry in history_entries
            for business_id in entry.result_business_ids
        }
        saved_businesses = {
            business.pk: business
            for business in Business.objects.filter(
                pk__in=saved_business_ids,
                is_published=True,
            ).select_related("category")
        }
        for entry in history_entries:
            entry.saved_businesses = [
                saved_businesses[business_id]
                for business_id in entry.result_business_ids
                if business_id in saved_businesses
            ]
    else:
        history_entries = []

    return render(
        request,
        "business_assistant.html",
        {
            "query": query,
            "query_error": query_error,
            "businesses": businesses,
            "searched": bool(query and not query_error),
            "history_entries": history_entries,
            "history_page_obj": history_page_obj,
        },
    )


@login_required
@require_POST
def business_assistant_history_delete(request, search_id):
    search = get_object_or_404(
        BusinessFinderSearch,
        pk=search_id,
        user=request.user,
    )
    search.delete()
    return redirect("business_assistant")


@login_required
@require_POST
def business_assistant_history_clear(request):
    BusinessFinderSearch.objects.filter(user=request.user).delete()
    return redirect("business_assistant")


def marketplace(request):
    form = MarketplaceFilterForm(request.GET or None)
    listings = MarketplaceListing.objects.filter(
        is_published=True,
        is_available=True,
        business__is_published=True,
    ).select_related("business", "category")

    if form.is_valid():
        filters = form.cleaned_data
        query = filters.get("q")
        if query:
            listings = listings.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(business__name__icontains=query)
                | Q(category__name__icontains=query)
            )
        if filters.get("category"):
            listings = listings.filter(category=filters["category"])
        if filters.get("listing_type"):
            listings = listings.filter(listing_type=filters["listing_type"])
        if filters.get("location"):
            location = filters["location"]
            listings = listings.filter(
                Q(business__location__icontains=location)
                | Q(business__county__icontains=location)
                | Q(business__town__icontains=location)
                | Q(business__physical_address__icontains=location)
            )
        if filters.get("min_price") is not None:
            listings = listings.filter(price__gte=filters["min_price"])
        if filters.get("max_price") is not None:
            listings = listings.filter(price__lte=filters["max_price"])

    sort = form.cleaned_data.get("sort") if form.is_valid() else "newest"
    if sort == "price_asc":
        listings = listings.order_by(F("price").asc(nulls_last=True), "name", "-pk")
    elif sort == "price_desc":
        listings = listings.order_by(F("price").desc(nulls_last=True), "name", "-pk")
    elif sort == "name":
        listings = listings.order_by("name", "-pk")
    else:
        listings = listings.order_by("-created_at", "-pk")

    paginator = Paginator(listings, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    pagination_query = request.GET.copy()
    pagination_query.pop("page", None)

    return render(
        request,
        "marketplace.html",
        {
            "listings": page_obj.object_list,
            "filter_form": form,
            "page_obj": page_obj,
            "pagination_query": pagination_query.urlencode(),
            "result_count": paginator.count,
        },
    )


def marketplace_listing_detail(request, listing_id):
    listing = get_object_or_404(
        MarketplaceListing.objects.select_related("business", "category"),
        pk=listing_id,
        is_published=True,
        is_available=True,
        business__is_published=True,
    )
    return render(
        request,
        "marketplace_listing_detail.html",
        {
            "listing": listing,
            "booking_form": ServiceBookingForm() if listing.listing_type == MarketplaceListing.SERVICE else None,
        },
    )


def marketplace_enquiry(request, listing_id):
    listing = get_object_or_404(
        MarketplaceListing.objects.select_related("business"),
        pk=listing_id,
        is_published=True,
        is_available=True,
        business__is_published=True,
    )
    form = MarketplaceEnquiryForm(
        request.POST or None,
        listing=listing,
    )
    if request.method == "POST" and form.is_valid():
        enquiry = form.save(commit=False)
        enquiry.listing = listing
        if request.user.is_authenticated:
            enquiry.customer = request.user
        enquiry.save()
        if listing.business.owner_id:
            _notify_user(
                listing.business.owner,
                message=f"New customer request for {listing.name}.",
                url=reverse("owner_enquiries", args=(listing.business_id,)),
            )
        messages.success(
            request,
            f"Your request has been sent to {listing.business.name}.",
        )
        return redirect(f"{reverse('marketplace')}#listing-{listing.pk}")
    return render(
        request,
        "marketplace_enquiry.html",
        {"listing": listing, "form": form},
        status=400 if request.method == "POST" else 200,
    )


def submit_business(request):
    form = BusinessSubmissionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Thanks! Your business has been submitted for review before it is listed.",
        )
        return redirect("business_submit")
    return render(request, "business_submit.html", {"form": form})


def _safe_account_redirect(request, fallback="business_dashboard"):
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(fallback)


def _account_password_form(user, data=None):
    form_class = PasswordChangeForm if user.has_usable_password() else SetPasswordForm
    return form_class(user, data)


def _notify_user(user, message, url):
    return notify_user(user, message, url)


def register(request):
    if request.user.is_authenticated:
        return redirect("business_dashboard")
    form = AccountRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Your MtaaBiz account has been created. Please log in to continue.",
        )
        return redirect("login")
    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("admin_reports" if request.user.is_superuser else "business_dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    next_url = request.POST.get("next") or request.GET.get("next", "")
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        auth_login(request, user)
        UserLoginEvent.objects.create(
            user=user,
            method=UserLoginEvent.METHOD_PASSWORD,
            ip_address=request.META.get("REMOTE_ADDR") or None,
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:300],
        )
        if not next_url and user.is_superuser:
            return redirect("admin_reports")
        return _safe_account_redirect(request)
    return render(request, "login.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    auth_logout(request)
    return redirect("index")


@login_required
def add_business(request):
    form = BusinessSubmissionForm(
        request.POST or None,
        initial={
            "contact_name": request.user.get_full_name(),
            "email": request.user.email,
        },
    )
    if request.method == "POST" and form.is_valid():
        business = form.save(commit=False)
        business.owner = request.user
        business.save()
        messages.success(
            request,
            "Your business was submitted for review. You can manage its details from your dashboard.",
        )
        return redirect("business_dashboard")
    return render(
        request,
        "business_submit.html",
        {"form": form, "owner_submission": True},
    )


@login_required
def business_dashboard(request):
    owned_businesses = Business.objects.filter(owner=request.user)
    business_cards = owned_businesses.select_related("category").annotate(
        listing_count=Count("marketplace_listings", distinct=True),
        enquiry_count=Count("marketplace_listings__enquiries", distinct=True),
        promotion_count=Count("promotions", distinct=True),
        booking_count=Count("marketplace_listings__bookings", distinct=True),
        profile_view_count=Count(
            "events",
            filter=Q(events__event_type=BusinessEvent.PROFILE_VIEW),
            distinct=True,
        ),
        contact_click_count=Count(
            "events",
            filter=Q(
                events__event_type__in=(
                    BusinessEvent.PHONE_CLICK,
                    BusinessEvent.EMAIL_CLICK,
                    BusinessEvent.WHATSAPP_CLICK,
                    BusinessEvent.WEBSITE_CLICK,
                )
            ),
            distinct=True,
        ),
    )
    stats = owned_businesses.aggregate(
        business_count=Count("pk", distinct=True),
        listing_count=Count("marketplace_listings", distinct=True),
        enquiry_count=Count("marketplace_listings__enquiries", distinct=True),
        promotion_count=Count("promotions", distinct=True),
        booking_count=Count("marketplace_listings__bookings", distinct=True),
        profile_view_count=Count(
            "events",
            filter=Q(events__event_type=BusinessEvent.PROFILE_VIEW),
            distinct=True,
        ),
        contact_click_count=Count(
            "events",
            filter=Q(
                events__event_type__in=(
                    BusinessEvent.PHONE_CLICK,
                    BusinessEvent.EMAIL_CLICK,
                    BusinessEvent.WHATSAPP_CLICK,
                    BusinessEvent.WEBSITE_CLICK,
                )
            ),
            distinct=True,
        ),
        review_count=Count(
            "reviews",
            filter=Q(reviews__is_approved=True),
            distinct=True,
        ),
    )
    return render(
        request,
        "owner_dashboard.html",
        {
            "businesses": business_cards,
            "claims": BusinessClaim.objects.filter(user=request.user).select_related("business"),
            "stats": stats,
        },
    )


def _get_owned_business(request, business_id):
    return get_object_or_404(Business, pk=business_id, owner=request.user)


@login_required
def owner_business_profile(request, business_id):
    business = _get_owned_business(request, business_id)
    form = BusinessSubmissionForm(
        request.POST or None,
        instance=business,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your business profile has been updated.")
        return redirect("business_dashboard")
    return render(
        request,
        "owner_business_profile.html",
        {"business": business, "form": form},
    )


@login_required
def owner_listings(request, business_id):
    business = _get_owned_business(request, business_id)
    form = MarketplaceListingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        listing = form.save(commit=False)
        listing.business = business
        listing.save()
        messages.success(request, "Listing saved and submitted for review.")
        return redirect("owner_listings", business_id=business.pk)
    return render(
        request,
        "owner_listings.html",
        {
            "business": business,
            "form": form,
            "listings": business.marketplace_listings.select_related("category"),
        },
    )


@login_required
def owner_listing_edit(request, listing_id):
    listing = get_object_or_404(
        MarketplaceListing,
        pk=listing_id,
        business__owner=request.user,
    )
    form = MarketplaceListingForm(request.POST or None, instance=listing)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your product or service has been updated.")
        return redirect("owner_listings", business_id=listing.business_id)
    return render(
        request,
        "owner_listing_edit.html",
        {"business": listing.business, "listing": listing, "form": form},
    )


@login_required
@require_POST
def owner_listing_delete(request, listing_id):
    listing = get_object_or_404(
        MarketplaceListing,
        pk=listing_id,
        business__owner=request.user,
    )
    business_id = listing.business_id
    listing.delete()
    messages.success(request, "The listing was removed.")
    return redirect("owner_listings", business_id=business_id)


@login_required
def owner_promotions(request, business_id):
    business = _get_owned_business(request, business_id)
    form = OwnerPromotionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        promotion = form.save(commit=False)
        promotion.business = business
        promotion.save()
        messages.success(request, "Promotion saved and submitted for review.")
        return redirect("owner_promotions", business_id=business.pk)
    return render(
        request,
        "owner_promotions.html",
        {
            "business": business,
            "form": form,
            "promotions": business.promotions.all(),
        },
    )


@login_required
def owner_promotion_edit(request, promotion_id):
    promotion = get_object_or_404(
        Promotion,
        pk=promotion_id,
        business__owner=request.user,
    )
    form = OwnerPromotionForm(request.POST or None, instance=promotion)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your promotion has been updated.")
        return redirect("owner_promotions", business_id=promotion.business_id)
    return render(
        request,
        "owner_promotion_edit.html",
        {"business": promotion.business, "promotion": promotion, "form": form},
    )


@login_required
@require_POST
def owner_promotion_delete(request, promotion_id):
    promotion = get_object_or_404(
        Promotion,
        pk=promotion_id,
        business__owner=request.user,
    )
    business_id = promotion.business_id
    promotion.delete()
    messages.success(request, "The promotion was removed.")
    return redirect("owner_promotions", business_id=business_id)


@login_required
def owner_enquiries(request, business_id):
    business = _get_owned_business(request, business_id)
    enquiries = MarketplaceEnquiry.objects.filter(
        listing__business=business
    ).select_related("listing").order_by("-created_at")
    return render(
        request,
        "owner_enquiries.html",
        {"business": business, "enquiries": enquiries},
    )


@login_required
@require_POST
def owner_enquiry_update(request, enquiry_id):
    enquiry = get_object_or_404(
        MarketplaceEnquiry,
        pk=enquiry_id,
        listing__business__owner=request.user,
    )
    form = EnquiryStatusForm(request.POST, instance=enquiry)
    if form.is_valid():
        enquiry = form.save()
        _notify_user(
            enquiry.customer,
            f"The business updated your request for {enquiry.listing.name}: {enquiry.get_status_display()}.",
            reverse("customer_dashboard"),
        )
        messages.success(request, "Enquiry status updated.")
    else:
        messages.error(request, "Choose a valid enquiry status.")
    return redirect("owner_enquiries", business_id=enquiry.listing.business_id)


@login_required
def business_verification(request):
    form = BusinessVerificationForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        verification = form.save(commit=False)
        verification.status = BusinessVerificationRequest.PENDING
        verification.save()
        messages.success(request, "Your verification details were submitted for review.")
        return redirect("business_dashboard")
    requests = BusinessVerificationRequest.objects.filter(
        business__owner=request.user
    ).select_related("business")
    return render(
        request,
        "business_verification.html",
        {
            "form": form,
            "has_owned_businesses": form.fields["business"].queryset.exists(),
            "verification_requests": requests,
        },
    )


@login_required
def owner_settings(request):
    profile_form = OwnerAccountForm(instance=request.user)
    password_form = _account_password_form(request.user)
    preferences, _ = UserNotificationPreference.objects.get_or_create(user=request.user)
    notification_form = NotificationPreferenceForm(instance=preferences)

    if request.method == "POST" and request.POST.get("action") == "profile":
        profile_form = OwnerAccountForm(request.POST, instance=request.user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your account details have been updated.")
            return redirect("owner_settings")
    elif request.method == "POST" and request.POST.get("action") == "password":
        password_form = _account_password_form(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed.")
            return redirect("owner_settings")
    elif request.method == "POST" and request.POST.get("action") == "notifications":
        notification_form = NotificationPreferenceForm(
            request.POST, instance=preferences
        )
        if notification_form.is_valid():
            notification_form.save()
            messages.success(request, "Your notification settings have been updated.")
            return redirect("owner_settings")

    return render(
        request,
        "owner_settings.html",
        {
            "active_page": "settings",
            "profile_form": profile_form,
            "password_form": password_form,
            "has_usable_password": request.user.has_usable_password(),
            "notification_form": notification_form,
            "google_accounts": SocialAccount.objects.filter(
                user=request.user, provider="google"
            ),
        },
    )


@login_required
def customer_dashboard(request):
    return render(
        request,
        "customer_dashboard.html",
        {
            "favorites": FavoriteBusiness.objects.filter(
                user=request.user, business__is_published=True
            ).select_related("business", "business__category"),
            "recent_businesses": RecentlyViewedBusiness.objects.filter(
                user=request.user, business__is_published=True
            ).select_related("business", "business__category")[:10],
            "enquiries": MarketplaceEnquiry.objects.filter(
                customer=request.user
            ).select_related("listing", "listing__business")[:10],
            "orders": MarketplaceEnquiry.objects.filter(
                customer=request.user,
                enquiry_type=MarketplaceEnquiry.ORDER_REQUEST,
            ).select_related("listing", "listing__business")[:10],
            "bookings": ServiceBooking.objects.filter(
                customer=request.user
            ).select_related("listing", "listing__business")[:10],
            "reviews": BusinessReview.objects.filter(
                customer=request.user
            ).select_related("business")[:10],
            "notifications": UserNotification.objects.filter(user=request.user)[:10],
            "unread_notifications": UserNotification.objects.filter(
                user=request.user, is_read=False
            ).count(),
        },
    )


@login_required
@require_POST
def notification_read(request, notification_id):
    notification = get_object_or_404(
        UserNotification, pk=notification_id, user=request.user
    )
    notification.is_read = True
    notification.save(update_fields=("is_read",))
    return redirect("customer_dashboard")


@login_required
def customer_settings(request):
    profile_form = OwnerAccountForm(instance=request.user)
    password_form = _account_password_form(request.user)
    preferences, _ = UserNotificationPreference.objects.get_or_create(user=request.user)
    notification_form = NotificationPreferenceForm(instance=preferences)

    if request.method == "POST" and request.POST.get("action") == "profile":
        profile_form = OwnerAccountForm(request.POST, instance=request.user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your account details have been updated.")
            return redirect("customer_settings")
    elif request.method == "POST" and request.POST.get("action") == "password":
        password_form = _account_password_form(request.user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Your password has been changed.")
            return redirect("customer_settings")
    elif request.method == "POST" and request.POST.get("action") == "notifications":
        notification_form = NotificationPreferenceForm(
            request.POST, instance=preferences
        )
        if notification_form.is_valid():
            notification_form.save()
            messages.success(request, "Your notification settings have been updated.")
            return redirect("customer_settings")

    return render(
        request,
        "customer_settings.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "has_usable_password": request.user.has_usable_password(),
            "notification_form": notification_form,
            "google_accounts": SocialAccount.objects.filter(
                user=request.user, provider="google"
            ),
        },
    )


@login_required
@require_POST
def service_booking(request, listing_id):
    listing = get_object_or_404(
        MarketplaceListing.objects.select_related("business"),
        pk=listing_id,
        listing_type=MarketplaceListing.SERVICE,
        is_published=True,
        is_available=True,
        business__is_published=True,
    )
    form = ServiceBookingForm(request.POST)
    if form.is_valid():
        booking = form.save(commit=False)
        booking.listing = listing
        booking.customer = request.user
        booking.save()
        _notify_user(
            listing.business.owner,
            f"New booking request for {listing.name}.",
            reverse("owner_bookings", args=(listing.business_id,)),
        )
        messages.success(request, "Your booking request was sent to the business.")
    else:
        messages.error(request, "Please choose a future date and time for your booking.")
    return redirect("business_detail", business_id=listing.business_id)


@login_required
@require_POST
def customer_booking_cancel(request, booking_id):
    booking = get_object_or_404(ServiceBooking, pk=booking_id, customer=request.user)
    if booking.status not in (ServiceBooking.PENDING, ServiceBooking.CONFIRMED):
        messages.error(request, "This booking can no longer be cancelled online.")
    else:
        booking.status = ServiceBooking.CANCELLED
        booking.save(update_fields=("status", "updated_at"))
        _notify_user(
            booking.listing.business.owner,
            f"A customer cancelled a booking for {booking.listing.name}.",
            reverse("owner_bookings", args=(booking.listing.business_id,)),
        )
        messages.success(request, "Your booking was cancelled.")
    return redirect("customer_dashboard")


@login_required
@require_POST
def business_review(request, business_id):
    business = get_object_or_404(Business, pk=business_id, is_published=True)
    if business.owner_id == request.user.pk:
        messages.error(request, "Business owners cannot review their own business.")
        return redirect("business_detail", business_id=business.pk)
    review = BusinessReview.objects.filter(
        business=business, customer=request.user
    ).first()
    was_approved = bool(review and review.is_approved)
    form = BusinessReviewForm(request.POST, instance=review)
    if form.is_valid():
        review = form.save(commit=False)
        review.business = business
        review.customer = request.user
        review.is_approved = False
        review.owner_response = ""
        review.save()
        if was_approved:
            refresh_business_rating(business.pk)
        _notify_user(
            business.owner,
            f"A new customer review for {business.name} is awaiting moderation.",
            reverse("owner_reviews", args=(business.pk,)),
        )
        messages.success(request, "Your review was submitted for moderation.")
    else:
        messages.error(request, "Please correct the review form and try again.")
    return redirect(f"{reverse('business_detail', args=(business.pk,))}#reviews")


@login_required
@require_POST
def business_report(request, business_id):
    business = get_object_or_404(Business, pk=business_id, is_published=True)
    if business.owner_id == request.user.pk:
        messages.error(request, "You cannot report a business you manage.")
        return redirect("business_detail", business_id=business.pk)
    form = BusinessReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.business = business
        report.reporter = request.user
        report.save()
        messages.success(request, "Thanks. The MtaaBiz team will review your report.")
    else:
        messages.error(request, "Choose a reason and add details before submitting a report.")
    return redirect(f"{reverse('business_detail', args=(business.pk,))}#report-business")


@login_required
def owner_bookings(request, business_id):
    business = _get_owned_business(request, business_id)
    bookings = ServiceBooking.objects.filter(
        listing__business=business
    ).select_related("listing", "customer")
    return render(
        request,
        "owner_bookings.html",
        {"business": business, "bookings": bookings},
    )


@login_required
@require_POST
def owner_booking_update(request, booking_id):
    booking = get_object_or_404(
        ServiceBooking, pk=booking_id, listing__business__owner=request.user
    )
    form = BookingStatusForm(request.POST, instance=booking)
    if form.is_valid():
        booking = form.save()
        _notify_user(
            booking.customer,
            f"Your booking for {booking.listing.name} is now {booking.get_status_display().lower()}.",
            reverse("customer_dashboard"),
        )
        messages.success(request, "Booking status updated.")
    else:
        messages.error(request, "Choose a valid booking status.")
    return redirect("owner_bookings", business_id=booking.listing.business_id)


@login_required
def owner_reviews(request, business_id):
    business = _get_owned_business(request, business_id)
    reviews = BusinessReview.objects.filter(
        business=business
    ).select_related("customer")
    return render(
        request,
        "owner_reviews.html",
        {"business": business, "reviews": reviews},
    )


@login_required
@require_POST
def owner_review_reply(request, review_id):
    review = get_object_or_404(
        BusinessReview, pk=review_id, business__owner=request.user, is_approved=True
    )
    form = BusinessReviewResponseForm(request.POST, instance=review)
    if form.is_valid():
        review = form.save()
        _notify_user(
            review.customer,
            f"{review.business.name} replied to your review.",
            reverse("customer_dashboard"),
        )
        messages.success(request, "Your response was saved.")
    else:
        messages.error(request, "Enter a response before saving.")
    return redirect("owner_reviews", business_id=review.business_id)


@login_required
def owner_analytics(request, business_id):
    business = _get_owned_business(request, business_id)
    cutoff = timezone.now() - timedelta(days=30)
    recent_events = BusinessEvent.objects.filter(
        business=business, created_at__gte=cutoff
    )
    metrics = recent_events.aggregate(
        profile_views=Count("pk", filter=Q(event_type=BusinessEvent.PROFILE_VIEW)),
        phone_clicks=Count("pk", filter=Q(event_type=BusinessEvent.PHONE_CLICK)),
        email_clicks=Count("pk", filter=Q(event_type=BusinessEvent.EMAIL_CLICK)),
        whatsapp_clicks=Count("pk", filter=Q(event_type=BusinessEvent.WHATSAPP_CLICK)),
        website_clicks=Count("pk", filter=Q(event_type=BusinessEvent.WEBSITE_CLICK)),
    )
    return render(
        request,
        "owner_analytics.html",
        {
            "business": business,
            "metrics": metrics,
            "recent_events": recent_events[:20],
            "booking_count": ServiceBooking.objects.filter(
                listing__business=business, created_at__gte=cutoff
            ).count(),
            "enquiry_count": MarketplaceEnquiry.objects.filter(
                listing__business=business, created_at__gte=cutoff
            ).count(),
            "review_count": business.reviews.filter(
                is_approved=True, created_at__gte=cutoff
            ).count(),
        },
    )


@login_required
def owner_advertisements(request, business_id):
    business = _get_owned_business(request, business_id)
    form = AdvertisementCampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save(commit=False)
        campaign.business = business
        campaign.save()
        messages.success(
            request,
            "Your advertisement request was sent for review. The MtaaBiz team will contact you about the manual payment.",
        )
        return redirect("owner_advertisements", business_id=business.pk)
    campaigns = business.advertisement_campaigns.all()
    return render(
        request,
        "owner_advertisements.html",
        {"business": business, "form": form, "campaigns": campaigns},
    )


@login_required
def owner_subscriptions(request, business_id):
    business = _get_owned_business(request, business_id)
    plans = ListingPlan.objects.filter(is_active=True)
    if request.method == "POST":
        plan = get_object_or_404(plans, pk=request.POST.get("plan"))
        status = (
            SubscriptionRequest.AWAITING_PAYMENT
            if plan.amount is not None
            else SubscriptionRequest.REQUESTED
        )
        SubscriptionRequest.objects.create(
            business=business,
            plan=plan,
            status=status,
            amount_due=plan.amount,
        )
        messages.success(
            request,
            "Your package request was submitted. MtaaBiz will confirm the manual payment details.",
        )
        return redirect("owner_subscriptions", business_id=business.pk)
    return render(
        request,
        "owner_subscriptions.html",
        {
            "business": business,
            "plans": plans,
            "requests": business.subscription_requests.select_related("plan"),
        },
    )


@login_required
@require_POST
def owner_manual_payment(request, payment_type, request_id):
    if payment_type == "subscription":
        target = get_object_or_404(
            SubscriptionRequest,
            pk=request_id,
            business__owner=request.user,
            status=SubscriptionRequest.AWAITING_PAYMENT,
        )
        business = target.business
        amount = target.amount_due
        relation = {"subscription": target}
    elif payment_type == "advertisement":
        target = get_object_or_404(
            AdvertisementCampaign,
            pk=request_id,
            business__owner=request.user,
            status=AdvertisementCampaign.AWAITING_PAYMENT,
        )
        business = target.business
        amount = target.amount_due
        relation = {"campaign": target}
    else:
        raise Http404("Unknown manual payment request.")

    if amount is None or amount <= 0:
        messages.error(request, "The amount due has not been configured by MtaaBiz.")
        route = "owner_subscriptions" if payment_type == "subscription" else "owner_advertisements"
        return redirect(route, business_id=business.pk)
    form = ManualPaymentSubmissionForm(request.POST)
    if form.is_valid():
        if ManualPayment.objects.filter(reference=form.cleaned_data["reference"]).exists():
            form.add_error("reference", "This payment reference has already been submitted.")
        elif target.payments.filter(status=ManualPayment.SUBMITTED).exists():
            messages.info(request, "A payment for this request is already awaiting confirmation.")
            return redirect(
                "owner_subscriptions" if payment_type == "subscription" else "owner_advertisements",
                business_id=business.pk,
            )
        else:
            payment = form.save(commit=False)
            payment.business = business
            payment.amount = amount
            payment.status = ManualPayment.SUBMITTED
            for key, value in relation.items():
                setattr(payment, key, value)
            try:
                payment.save()
            except IntegrityError:
                if ManualPayment.objects.filter(reference=payment.reference).exists():
                    messages.error(request, "This payment reference has already been submitted.")
                    return redirect(
                        "owner_subscriptions" if payment_type == "subscription" else "owner_advertisements",
                        business_id=business.pk,
                    )
                raise
            messages.success(request, "Payment details submitted for manual confirmation.")
            return redirect(
                "owner_subscriptions" if payment_type == "subscription" else "owner_advertisements",
                business_id=business.pk,
            )
    messages.error(request, "Please provide a valid payment method and reference.")
    return redirect(
        "owner_subscriptions" if payment_type == "subscription" else "owner_advertisements",
        business_id=business.pk,
    )


@login_required
def claim_business(request):
    form = BusinessClaimForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        claim = form.save(commit=False)
        claim.user = request.user
        claim.save()
        messages.success(request, "Your claim was submitted for review.")
        return redirect("business_dashboard")
    return render(
        request,
        "claim_business.html",
        {
            "form": form,
            "has_claimable_businesses": form.fields["business"].queryset.exists(),
        },
    )


def pricing(request):
    return render(
        request,
        "pricing.html",
        {"plans": ListingPlan.objects.filter(is_active=True)},
    )


@staff_member_required
def admin_reports(request):
    month_start = timezone.localdate().replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    events = BusinessEvent.objects.filter(
        created_at__date__gte=month_start,
        created_at__date__lt=next_month,
    )
    payment_summary = ManualPayment.objects.filter(
        status=ManualPayment.CONFIRMED,
        reviewed_at__date__gte=month_start,
        reviewed_at__date__lt=next_month,
    ).aggregate(count=Count("pk"), revenue=Sum("amount"))
    login_totals = UserLoginEvent.objects.aggregate(
        total_logins=Count("pk"),
        password_logins=Count("pk", filter=Q(method=UserLoginEvent.METHOD_PASSWORD)),
        google_logins=Count("pk", filter=Q(method=UserLoginEvent.METHOD_GOOGLE)),
        unique_users=Count("user", distinct=True),
    )
    monthly_logins = UserLoginEvent.objects.filter(
        created_at__date__gte=month_start,
        created_at__date__lt=next_month,
    ).aggregate(total=Count("pk"), unique_users=Count("user", distinct=True))
    return render(
        request,
        "admin_reports.html",
        {
            "business_count": Business.objects.count(),
            "published_business_count": Business.objects.filter(is_published=True).count(),
            "pending_business_count": Business.objects.filter(is_published=False).count(),
            "pending_reviews": BusinessReview.objects.filter(is_approved=False).count(),
            "pending_business_reports": BusinessReport.objects.filter(
                status=BusinessReport.PENDING
            ).count(),
            "pending_claims": BusinessClaim.objects.filter(status=BusinessClaim.PENDING).count(),
            "pending_verifications": BusinessVerificationRequest.objects.filter(
                status=BusinessVerificationRequest.PENDING
            ).count(),
            "active_campaigns": AdvertisementCampaign.objects.filter(
                status=AdvertisementCampaign.ACTIVE
            ).count(),
            "active_subscriptions": SubscriptionRequest.objects.filter(
                status=SubscriptionRequest.ACTIVE
            ).count(),
            "event_metrics": events.values("event_type").annotate(total=Count("pk")).order_by(
                "event_type"
            ),
            "monthly_payments": payment_summary["count"],
            "monthly_revenue": payment_summary["revenue"] or 0,
            "top_businesses": Business.objects.filter(is_published=True)
            .annotate(
                profile_views=Count(
                    "events",
                    filter=Q(events__event_type=BusinessEvent.PROFILE_VIEW),
                )
            )
            .order_by("-profile_views", "name")[:10],
            "login_totals": login_totals,
            "monthly_logins": monthly_logins,
            "recent_logins": UserLoginEvent.objects.select_related("user")[:15],
            "login_method_breakdown": UserLoginEvent.objects.values("method")
            .annotate(total=Count("pk"))
            .order_by("method"),
        },
    )


@staff_member_required
def admin_business_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="mtaabiz-business-report.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ("Business", "Category", "County", "Town", "Owner", "Published", "Verified", "Created")
    )
    for business in Business.objects.select_related("category", "owner").order_by("name"):
        writer.writerow(
            (
                business.name,
                business.category.name if business.category else "",
                business.county,
                business.town,
                business.owner.username if business.owner else "",
                business.is_published,
                business.is_verified,
                business.created_at.isoformat(),
            )
        )
    return response


@staff_member_required
def admin_revenue_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="mtaabiz-confirmed-payments.csv"'
    writer = csv.writer(response)
    writer.writerow(
        ("Business", "Purpose", "Amount KSh", "Method", "Reference", "Confirmed at")
    )
    payments = ManualPayment.objects.filter(status=ManualPayment.CONFIRMED).select_related(
        "business", "subscription__plan", "campaign"
    )
    for payment in payments:
        purpose = (
            f"Subscription: {payment.subscription.plan.name}"
            if payment.subscription_id
            else f"Advertisement: {payment.campaign.title}"
        )
        writer.writerow(
            (
                payment.business.name,
                purpose,
                payment.amount,
                payment.get_method_display(),
                payment.reference,
                payment.reviewed_at.isoformat() if payment.reviewed_at else "",
            )
        )
    return response


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Thanks for contacting us. We will be in touch.")
        return redirect("contact")
    if request.method == "POST":
        messages.error(request, "Please correct the errors in the contact form.")
    return render(
        request,
        "contact.html",
        {
            "contact_form": form,
            "site_settings": SiteSettings.objects.first(),
            "social_links": SocialLink.objects.filter(is_active=True),
        },
        status=400 if request.method == "POST" else 200,
    )


def subscribe(request):
    if request.method != "POST":
        return redirect(f"{reverse('index')}#footer")

    form = NewsletterForm(request.POST)
    if form.is_valid():
        _, created = NewsletterSubscription.objects.get_or_create(
            email=form.cleaned_data["email"]
        )
        if created:
            messages.success(request, "You are subscribed to the MtaaBiz newsletter.")
        else:
            messages.info(request, "That email is already subscribed.")
    else:
        messages.error(request, "Enter a valid email address to subscribe.")
    return redirect(f"{reverse('index')}#footer")

# (READ-Fetch): Use the function below to fetch information from the database & display to frontend
def show(request):
    contacts = Contact.objects.order_by("-id")
    return render(request, "show.html", {"all": contacts})


def dashboard_settings(request):
    return render(request, "dashboard_settings.html")


# For delete operation to work, the below function is used to delete a contact from the database based on the provided id. After deletion, it redirects to the show page to display the updated list of contacts.
def delete(request, id):
    contactinfo = Contact.objects.get(id=id)
    contactinfo.delete()
    return redirect('/show')

# For edit operation to work, the below function is used to edit a contact from the database based on the provided id. After editing, it redirects to the show page to display the updated list of contacts.
def edit(request, id):
    editcontactinfo = get_object_or_404(Contact, id=id)
    if request.method == 'POST':
        editcontactinfo.name = request.POST.get('name')
        editcontactinfo.email = request.POST.get('email')
        editcontactinfo.subject = request.POST.get('subject')
        editcontactinfo.message = request.POST.get('message')
        editcontactinfo.save()
        return redirect('show')
    else:
        return render(request, 'edit.html', {"contactinfo": editcontactinfo})