from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from .admin import BusinessReviewAdmin, ManualPaymentAdmin
from .notifications import notify_user
from .models import (
    AdvertisementCampaign,
    BusinessEvent,
    BusinessReport,
    BusinessReview,
    Business,
    BusinessClaim,
    BusinessVerificationRequest,
    Category,
    Contact,
    MarketplaceCategory,
    MarketplaceEnquiry,
    MarketplaceListing,
    FavoriteBusiness,
    ListingPlan,
    ManualPayment,
    NewsletterSubscription,
    Promotion,
    RecentlyViewedBusiness,
    ServiceBooking,
    SubscriptionRequest,
    UserLoginEvent,
    UserNotification,
    UserNotificationPreference,
    ContentArticle,
    Testimonial,
)


class HomeDirectoryTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Food and Drink", slug="food-and-drink", icon_class="bi bi-cup-hot"
        )
        self.business = Business.objects.create(
            name="Bondo Cafe",
            category=self.category,
            description="A neighborhood coffee shop",
            offerings="Coffee, pastries, breakfast",
            location="Bondo Town",
            phone="0700123456",
            image_url="https://example.com/bondo-cafe.jpg",
            is_published=True,
            is_featured=True,
            is_popular=True,
            is_verified=True,
        )
        Business.objects.create(
            name="Hidden Cafe",
            category=self.category,
            description="Not yet reviewed",
            offerings="Coffee",
            location="Bondo Town",
        )

    def test_homepage_renders_database_content_and_live_offers(self):
        Promotion.objects.create(
            business=self.business,
            title="Breakfast special",
            starts_on=timezone.localdate(),
            is_published=True,
        )
        Testimonial.objects.create(
            name="Local customer",
            quote="A great neighborhood find.",
            is_published=True,
        )

        response = self.client.get(reverse("index"))

        self.assertContains(response, "Food and Drink")
        self.assertContains(response, "Bondo Cafe")
        self.assertContains(response, "Breakfast special")
        self.assertContains(response, "A great neighborhood find.")
        self.assertNotContains(response, "Hidden Cafe")
        self.assertContains(response, 'id="testimonials"')
        self.assertContains(response, reverse("featured_businesses"))
        self.assertContains(response, 'href="%s">Login</a>' % reverse("login"))
        self.assertContains(response, 'href="%s">Register</a>' % reverse("register"))
        self.assertContains(response, "Coffee, pastries, breakfast")
        self.assertContains(response, "Bondo Town")
        self.assertContains(response, "0700123456")
        self.assertContains(response, "https://example.com/bondo-cafe.jpg")
        self.assertContains(response, reverse("register"))

    def test_about_and_deals_navigation_pages_render(self):
        Promotion.objects.create(
            business=self.business,
            title="Community breakfast offer",
            description="Save on breakfast this week.",
            starts_on=timezone.localdate(),
            ends_on=timezone.localdate() + timedelta(days=2),
            is_published=True,
        )

        home = self.client.get(reverse("index"))
        about_response = self.client.get(reverse("about"))
        deals_response = self.client.get(reverse("deals"))

        self.assertContains(home, f'href="{reverse("about")}"')
        self.assertContains(home, f'href="{reverse("deals")}"')
        self.assertContains(home, f'href="{reverse("contact")}"')
        self.assertContains(about_response, "Local businesses deserve to be")
        self.assertContains(about_response, reverse("businesses"))
        self.assertContains(deals_response, "Community breakfast offer")
        self.assertContains(deals_response, "Save on breakfast this week.")

    def test_footer_social_links_open_requested_platforms_in_new_tabs(self):
        response = self.client.get(reverse("index"))

        for platform, url in (
            ("Instagram", "https://www.instagram.com/"),
            ("Facebook", "https://www.facebook.com/"),
            ("LinkedIn", "https://www.linkedin.com/"),
        ):
            with self.subTest(platform=platform):
                self.assertContains(response, f'href="{url}"')
                self.assertContains(response, f'aria-label="{platform}"')

        self.assertContains(response, 'target="_blank" rel="noopener noreferrer"')
        self.assertNotContains(response, "Social links coming soon")

    def test_deals_page_hides_expired_and_unpublished_promotions(self):
        Promotion.objects.create(
            business=self.business,
            title="Expired deal",
            ends_on=timezone.localdate() - timedelta(days=1),
            is_published=True,
        )
        Promotion.objects.create(
            business=self.business,
            title="Draft deal",
            is_published=False,
        )

        response = self.client.get(reverse("deals"))

        self.assertNotContains(response, "Expired deal")
        self.assertNotContains(response, "Draft deal")
        self.assertContains(response, "No active deals just yet")

    def test_home_category_bar_links_categories_and_lists_additional_categories(self):
        extra_categories = [
            Category.objects.create(
                name=f"Category {index}",
                slug=f"category-{index}",
                icon_class="bi bi-grid",
                display_order=index,
            )
            for index in range(2, 9)
        ]

        response = self.client.get(reverse("index"))

        self.assertContains(response, 'aria-label="Browse business categories"')
        self.assertContains(response, 'class="hero-category-icon category-orange"')
        self.assertContains(
            response,
            f'href="{reverse("businesses")}?category={self.category.slug}"',
        )
        self.assertContains(
            response,
            f'href="{reverse("businesses")}?category={extra_categories[-1].slug}"',
        )
        self.assertContains(response, "More")

    def test_requested_business_categories_are_seeded_and_available_in_filters(self):
        requested_categories = {
            "restaurants-hotels",
            "shopping-retail",
            "beauty-personal-care",
            "health-wellness",
            "education-training",
            "construction-hardware",
            "transport-logistics",
            "technology-ict",
            "professional-services",
            "real-estate-property",
            "automotive-services",
            "events-entertainment",
        }

        self.assertTrue(
            requested_categories.issubset(
                set(Category.objects.filter(slug__in=requested_categories).values_list("slug", flat=True))
            )
        )

        response = self.client.get(reverse("businesses"))
        self.assertContains(response, "Beauty &amp; Personal Care")
        self.assertContains(response, "Professional Services")
        self.assertContains(response, "Real Estate &amp; Property")
        self.assertContains(response, "Automotive Services")
        self.assertContains(response, "Events &amp; Entertainment")

    def test_featured_business_directory_shows_all_published_featured_details(self):
        Business.objects.create(
            name="Featured Tailor",
            description="Custom tailoring for the neighborhood.",
            offerings="Alterations and made-to-measure clothing",
            location="Bondo Town",
            phone="0711222333",
            image_url="https://example.com/featured-tailor.jpg",
            is_published=True,
            is_featured=True,
        )
        Business.objects.create(
            name="Regular Grocery",
            location="Bondo Town",
            is_published=True,
        )

        response = self.client.get(reverse("featured_businesses"))

        self.assertContains(response, "Bondo Cafe")
        self.assertContains(response, "Featured Tailor")
        self.assertContains(response, "https://example.com/bondo-cafe.jpg")
        self.assertContains(response, "https://example.com/featured-tailor.jpg")
        self.assertContains(response, "A neighborhood coffee shop")
        self.assertContains(response, "Alterations and made-to-measure clothing")
        self.assertNotContains(response, "Regular Grocery")
        self.assertNotContains(response, "Hidden Cafe")

    def test_search_matches_offerings_and_excludes_unpublished_businesses(self):
        response = self.client.get(reverse("businesses"), {"q": "pastries"})

        self.assertContains(response, "Bondo Cafe")
        self.assertNotContains(response, "Hidden Cafe")

    def test_category_and_location_filters_can_be_combined(self):
        response = self.client.get(
            reverse("businesses"),
            {"category": "food-and-drink", "location": "Bondo"},
        )

        self.assertContains(response, "Bondo Cafe")
        self.assertNotContains(response, "Hidden Cafe")

    def test_business_search_matches_structured_address_fields(self):
        Business.objects.create(
            name="Kisumu Repair Shop",
            county="Kisumu County",
            town="Bondo",
            physical_address="Market Street",
            location="Bondo",
            is_published=True,
        )

        county_response = self.client.get(reverse("businesses"), {"location": "Kisumu"})
        address_response = self.client.get(reverse("businesses"), {"location": "Market"})

        self.assertContains(county_response, "Kisumu Repair Shop")
        self.assertContains(address_response, "Kisumu Repair Shop")

    def test_expired_promotions_are_not_shown(self):
        Promotion.objects.create(
            business=self.business,
            title="Expired promotion",
            ends_on=timezone.localdate() - timedelta(days=1),
            is_published=True,
        )

        response = self.client.get(reverse("index"))

        self.assertNotContains(response, "Expired promotion")


class PublicFormTests(TestCase):
    def test_contact_dashboard_displays_messages_and_actions(self):
        first = Contact.objects.create(
            name="Alex Visitor",
            email="alex@example.com",
            subject="Business listing",
            message="How can I list my shop?",
        )
        Contact.objects.create(
            name="Sam Customer",
            email="sam@example.com",
            subject="Marketplace question",
            message="Can I request a quote?",
        )

        response = self.client.get(reverse("show"))

        self.assertContains(response, "Contact inbox")
        self.assertContains(response, "Alex Visitor")
        self.assertContains(response, "Sam Customer")
        self.assertContains(response, "2</strong>")
        self.assertContains(response, reverse("edit", args=[first.pk]))
        self.assertContains(response, reverse("delete", args=[first.pk]))
        self.assertContains(response, 'id="contact-search"')
        self.assertContains(response, reverse("dashboard_settings"))
        self.assertContains(response, f'data-contact-id="{first.pk}"')
        self.assertGreater(
            response.content.index(b"</nav>"),
            response.content.index(b'href="/show/settings/"'),
        )

    def test_contact_dashboard_shows_empty_state(self):
        response = self.client.get(reverse("show"))

        self.assertContains(response, "Your inbox is clear")

    def test_contact_dashboard_settings_page_shows_preferences(self):
        response = self.client.get(reverse("dashboard_settings"))

        self.assertContains(response, "Dashboard settings")
        self.assertContains(response, "Compact inbox")
        self.assertContains(response, "Newest first")
        self.assertContains(response, reverse("show"))
        self.assertContains(response, 'id="dashboard-settings-form"')

    def test_edit_contact_page_shows_existing_values_and_saves_changes(self):
        contact = Contact.objects.create(
            name="Alex Visitor",
            email="alex@example.com",
            subject="Business listing",
            message="How can I list my shop?",
        )

        response = self.client.get(reverse("edit", args=[contact.pk]))

        self.assertContains(response, "Update message details")
        self.assertContains(response, f'value="{contact.name}"')
        self.assertContains(response, f'value="{contact.email}"')
        self.assertContains(response, "How can I list my shop?")

        response = self.client.post(
            reverse("edit", args=[contact.pk]),
            {
                "name": "Alex Updated",
                "email": "alex.updated@example.com",
                "subject": "Updated subject",
                "message": "Updated message body.",
            },
        )

        self.assertRedirects(response, reverse("show"))
        contact.refresh_from_db()
        self.assertEqual(contact.name, "Alex Updated")
        self.assertEqual(contact.email, "alex.updated@example.com")
        self.assertEqual(contact.subject, "Updated subject")
        self.assertEqual(contact.message, "Updated message body.")

    def test_business_submission_stays_unpublished_until_review(self):
        category = Category.objects.get(slug="restaurants-hotels")
        response = self.client.post(
            reverse("business_submit"),
            {
                "contact_name": "A Business Owner",
                "email": "owner@example.com",
                "name": "New Local Shop",
                "category": category.pk,
                "phone": "0700000000",
                "county": "Kisumu County",
                "town": "Bondo",
                "physical_address": "Market Street, Plot 10",
                "description": "A neighborhood store",
                "offerings": "Groceries",
                "logo_url": "https://example.com/new-local-shop-logo.png",
                "cover_image_url": "https://example.com/new-local-shop-cover.jpg",
                "opening_hours": "Mon-Sat, 8:00 AM-6:00 PM",
                "facebook_url": "https://facebook.com/newlocalshop",
                "instagram_url": "https://instagram.com/newlocalshop",
                "tiktok_url": "https://tiktok.com/@newlocalshop",
                "x_url": "https://x.com/newlocalshop",
                "linkedin_url": "https://linkedin.com/company/newlocalshop",
                "website_url": "https://newlocalshop.example.com",
            },
        )

        self.assertRedirects(response, reverse("business_submit"))
        submitted = Business.objects.get(name="New Local Shop")
        self.assertFalse(submitted.is_published)
        self.assertFalse(submitted.is_verified)
        self.assertEqual(submitted.county, "Kisumu County")
        self.assertEqual(submitted.town, "Bondo")
        self.assertEqual(submitted.physical_address, "Market Street, Plot 10")
        self.assertEqual(submitted.logo_url, "https://example.com/new-local-shop-logo.png")
        self.assertEqual(
            submitted.cover_image_url,
            "https://example.com/new-local-shop-cover.jpg",
        )
        self.assertEqual(submitted.image_url, submitted.cover_image_url)
        self.assertEqual(
            submitted.formatted_location,
            "Market Street, Plot 10, Bondo, Kisumu County",
        )
        self.assertEqual(submitted.opening_hours, "Mon-Sat, 8:00 AM-6:00 PM")
        self.assertEqual(submitted.facebook_url, "https://facebook.com/newlocalshop")
        self.assertEqual(submitted.instagram_url, "https://instagram.com/newlocalshop")
        self.assertEqual(submitted.tiktok_url, "https://tiktok.com/@newlocalshop")
        self.assertEqual(submitted.x_url, "https://x.com/newlocalshop")
        self.assertEqual(
            submitted.linkedin_url,
            "https://linkedin.com/company/newlocalshop",
        )
        self.assertEqual(submitted.website_url, "https://newlocalshop.example.com")

    def test_business_submission_form_contains_requested_profile_fields(self):
        response = self.client.get(reverse("business_submit"))

        for label in (
            "Business name",
            "Business category",
            "Owner&#x27;s name",
            "Phone number",
            "Business email",
            "County",
            "Town",
            "Physical address",
            "Business description",
            "Products and services",
            "Business logo URL (optional)",
            "Cover photo URL (optional)",
            "Business opening hours (optional)",
            "Facebook page URL (optional)",
            "Website URL (optional)",
        ):
            self.assertContains(response, label)

    def test_newsletter_subscription_normalizes_email_and_is_idempotent(self):
        url = reverse("newsletter_subscribe")
        response = self.client.post(url, {"email": "  PERSON@EXAMPLE.COM  "})
        self.assertRedirects(response, f"{reverse('index')}#footer")
        response = self.client.post(url, {"email": "person@example.com"})

        self.assertRedirects(response, f"{reverse('index')}#footer")
        self.assertEqual(NewsletterSubscription.objects.count(), 1)

    def test_contact_form_saves_valid_messages(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Visitor",
                "email": "visitor@example.com",
                "subject": "Question",
                "message": "How can I list my business?",
            },
        )

        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(Contact.objects.count(), 1)

    def test_contact_page_renders_form_and_homepage_no_longer_contains_it(self):
        response = self.client.get(reverse("contact"))
        home = self.client.get(reverse("index"))

        self.assertContains(response, "Let’s get in touch.")
        self.assertContains(response, 'action="/contact/"')
        self.assertNotContains(home, 'class="home-contact-form"')

    def test_invalid_contact_submission_stays_on_contact_page(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "",
                "email": "invalid",
                "subject": "",
                "message": "",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Please correct the errors", status_code=400)
        self.assertEqual(Contact.objects.count(), 0)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class OwnerAccountWorkflowTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.owner = self.user_model.objects.create_user(
            username="business-owner",
            email="owner@example.com",
            password="MtaaBiz-StrongPass-2026!",
            first_name="Business",
            last_name="Owner",
        )
        self.other_owner = self.user_model.objects.create_user(
            username="other-owner",
            email="other@example.com",
            password="MtaaBiz-OtherPass-2026!",
        )
        self.category = Category.objects.get(slug="restaurants-hotels")
        self.marketplace_category = MarketplaceCategory.objects.create(
            name="Owner Products",
            slug="owner-products",
        )
        self.business = Business.objects.create(
            name="Owner Cafe",
            owner=self.owner,
            category=self.category,
            location="Bondo",
            town="Bondo",
            is_published=True,
        )
        self.client.force_login(self.owner)

    def test_registration_redirects_to_login_and_business_submission_is_owner_linked(self):
        self.client.logout()
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-owner",
                "first_name": "New",
                "last_name": "Owner",
                "email": "new-owner@example.com",
                "password1": "MtaaBiz-NewStrongPass-2026!",
                "password2": "MtaaBiz-NewStrongPass-2026!",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = self.user_model.objects.get(username="new-owner")
        self.assertFalse(self.client.session.get("_auth_user_id"))

        self.client.force_login(user)
        response = self.client.post(
            reverse("add_business"),
            {
                "name": "New Owner Shop",
                "category": self.category.pk,
                "contact_name": "New Owner",
                "phone": "0700000000",
                "email": "shop@example.com",
                "county": "Siaya County",
                "town": "Bondo",
                "physical_address": "Main Street",
                "description": "A local shop.",
                "offerings": "Groceries",
            },
        )

        self.assertRedirects(response, reverse("business_dashboard"))
        submitted = Business.objects.get(name="New Owner Shop")
        self.assertEqual(submitted.owner, user)
        self.assertFalse(submitted.is_published)

    def test_login_redirect_and_owner_dashboard_scope(self):
        self.client.logout()
        response = self.client.get(reverse("business_dashboard"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('business_dashboard')}",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "business-owner",
                "password": "MtaaBiz-StrongPass-2026!",
            },
        )
        self.assertRedirects(response, reverse("business_dashboard"))

        Business.objects.create(
            name="Private Other Shop",
            owner=self.other_owner,
            location="Kisumu",
        )
        response = self.client.get(reverse("business_dashboard"))

        self.assertContains(response, "Owner Cafe")
        self.assertNotContains(response, "Private Other Shop")

    def test_owner_can_manage_only_their_products_promotions_and_enquiries(self):
        other_business = Business.objects.create(
            name="Other Owner Cafe",
            owner=self.other_owner,
            location="Kisumu",
        )
        response = self.client.post(
            reverse("owner_listings", args=[self.business.pk]),
            {
                "name": "Coffee Beans",
                "category": self.marketplace_category.pk,
                "listing_type": MarketplaceListing.PRODUCT,
                "description": "Fresh local coffee beans.",
                "price": "850.00",
                "is_available": "on",
            },
        )

        self.assertRedirects(response, reverse("owner_listings", args=[self.business.pk]))
        listing = MarketplaceListing.objects.get(name="Coffee Beans")
        self.assertEqual(listing.business, self.business)
        self.assertFalse(listing.is_published)
        self.assertEqual(
            self.client.get(reverse("owner_listings", args=[other_business.pk])).status_code,
            404,
        )

        response = self.client.post(
            reverse("owner_promotions", args=[self.business.pk]),
            {
                "title": "Coffee Week",
                "description": "Save on coffee.",
                "starts_on": timezone.localdate().isoformat(),
                "ends_on": (timezone.localdate() + timedelta(days=3)).isoformat(),
            },
        )
        self.assertRedirects(response, reverse("owner_promotions", args=[self.business.pk]))
        promotion = Promotion.objects.get(title="Coffee Week")
        self.assertEqual(promotion.business, self.business)
        self.assertFalse(promotion.is_published)

        enquiry = MarketplaceEnquiry.objects.create(
            listing=listing,
            customer_name="A Customer",
            email="customer@example.com",
            message="Is this available?",
        )
        response = self.client.post(
            reverse("owner_enquiry_update", args=[enquiry.pk]),
            {"status": MarketplaceEnquiry.CONTACTED},
        )
        self.assertRedirects(response, reverse("owner_enquiries", args=[self.business.pk]))
        enquiry.refresh_from_db()
        self.assertEqual(enquiry.status, MarketplaceEnquiry.CONTACTED)

        other_listing = MarketplaceListing.objects.create(
            business=other_business,
            name="Private Listing",
            description="Not yours.",
        )
        other_enquiry = MarketplaceEnquiry.objects.create(
            listing=other_listing,
            customer_name="Private Customer",
            email="private@example.com",
            message="Private enquiry.",
        )
        self.assertEqual(
            self.client.post(
                reverse("owner_enquiry_update", args=[other_enquiry.pk]),
                {"status": MarketplaceEnquiry.CONTACTED},
            ).status_code,
            404,
        )

    def test_verification_and_claim_requests_are_owner_scoped(self):
        response = self.client.post(
            reverse("business_verification"),
            {
                "business": self.business.pk,
                "registration_number": "BR-1045",
                "contact_name": "Business Owner",
                "phone": "0700000000",
                "email": "owner@example.com",
                "notes": "Registration documents are available on request.",
            },
        )
        self.assertRedirects(response, reverse("business_dashboard"))
        verification = BusinessVerificationRequest.objects.get(business=self.business)
        self.assertEqual(verification.status, BusinessVerificationRequest.PENDING)

        unclaimed = Business.objects.create(
            name="Existing Public Shop",
            location="Bondo",
            is_published=True,
        )
        response = self.client.post(
            reverse("claim_business"),
            {
                "business": unclaimed.pk,
                "email": "owner@example.com",
                "phone": "0700000000",
                "message": "I own this shop.",
            },
        )
        self.assertRedirects(response, reverse("business_dashboard"))
        claim = BusinessClaim.objects.get(business=unclaimed, user=self.owner)
        self.assertEqual(claim.status, BusinessClaim.PENDING)
        self.assertContains(self.client.get(reverse("business_dashboard")), unclaimed.name)

    def test_pricing_page_is_public(self):
        self.client.logout()
        response = self.client.get(reverse("pricing"))

        self.assertContains(response, "Listing packages")
        self.assertContains(response, reverse("add_business"))

    def test_owner_can_update_account_details_and_password(self):
        response = self.client.post(
            reverse("owner_settings"),
            {
                "action": "profile",
                "first_name": "Updated",
                "last_name": "Owner",
                "email": "updated-owner@example.com",
            },
        )
        self.assertRedirects(response, reverse("owner_settings"))
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.first_name, "Updated")
        self.assertEqual(self.owner.email, "updated-owner@example.com")

        response = self.client.post(
            reverse("owner_settings"),
            {
                "action": "password",
                "old_password": "MtaaBiz-StrongPass-2026!",
                "new_password1": "A-Different-StrongPass-2026!",
                "new_password2": "A-Different-StrongPass-2026!",
            },
        )
        self.assertRedirects(response, reverse("owner_settings"))
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.check_password("A-Different-StrongPass-2026!"))

    @override_settings(GOOGLE_OAUTH_ENABLED=False, SOCIALACCOUNT_PROVIDERS={})
    def test_google_sign_in_controls_explain_missing_configuration(self):
        self.client.logout()
        for url in (reverse("login"), reverse("register")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "Continue with Google")
                self.assertContains(response, "disabled")
                self.assertContains(response, "will be available after it is configured")

    @override_settings(
        GOOGLE_OAUTH_ENABLED=True,
        SOCIALACCOUNT_PROVIDERS={
            "google": {
                "APP": {
                    "client_id": "test-client-id",
                    "secret": "test-client-secret",
                    "key": "",
                },
                "SCOPE": ["profile", "email"],
            }
        },
    )
    def test_google_sign_in_and_connected_accounts_render(self):
        self.client.logout()
        for url in (reverse("login"), reverse("register")):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "Continue with Google")
                self.assertContains(response, reverse("google_login"))

        response = self.client.post(f"{reverse('google_login')}?process=login")
        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts.google.com", response["Location"])

        self.client.force_login(self.owner)
        google_account = SocialAccount.objects.create(
            user=self.owner,
            provider="google",
            uid="google-owner-uid",
            extra_data={"email": self.owner.email},
        )
        response = self.client.get(reverse("owner_settings"))
        self.assertContains(response, "Google connected")
        self.assertContains(response, self.owner.email)
        self.assertContains(response, reverse("socialaccount_connections"))

        response = self.client.get(reverse("socialaccount_connections"))
        self.assertContains(response, "Connected accounts")
        self.assertContains(response, self.owner.email)
        self.assertContains(response, str(google_account.pk))
        self.assertContains(response, "Disconnect selected account")

        response = self.client.post(
            reverse("socialaccount_connections"),
            {"account": google_account.pk},
        )
        self.assertRedirects(response, reverse("socialaccount_connections"))
        self.assertFalse(SocialAccount.objects.filter(pk=google_account.pk).exists())

    def test_social_only_user_can_set_a_password_from_account_settings(self):
        user = self.user_model.objects.create_user(
            username="google-only",
            email="google-only@example.com",
            password=None,
        )
        self.assertFalse(user.has_usable_password())
        self.client.force_login(user)

        response = self.client.get(reverse("owner_settings"))
        self.assertContains(response, "Set a password")

        response = self.client.post(
            reverse("owner_settings"),
            {
                "action": "password",
                "new_password1": "A-Google-Account-StrongPass-2026!",
                "new_password2": "A-Google-Account-StrongPass-2026!",
            },
        )
        self.assertRedirects(response, reverse("owner_settings"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("A-Google-Account-StrongPass-2026!"))

    def test_owner_account_and_management_pages_render(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("register")).status_code, 200)
        self.assertEqual(self.client.get(reverse("login")).status_code, 200)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("add_business")).status_code, 200)

        listing = MarketplaceListing.objects.create(
            business=self.business,
            category=self.marketplace_category,
            name="House Blend",
            description="Locally roasted coffee.",
        )
        promotion = Promotion.objects.create(
            business=self.business,
            title="Weekend special",
        )
        enquiry = MarketplaceEnquiry.objects.create(
            listing=listing,
            customer_name="A Customer",
            email="customer@example.com",
            message="Can I order?",
        )
        unclaimed = Business.objects.create(
            name="Available Listing",
            location="Bondo",
            is_published=True,
        )

        page_urls = (
            reverse("owner_business_profile", args=[self.business.pk]),
            reverse("owner_listings", args=[self.business.pk]),
            reverse("owner_listing_edit", args=[listing.pk]),
            reverse("owner_promotions", args=[self.business.pk]),
            reverse("owner_promotion_edit", args=[promotion.pk]),
            reverse("owner_enquiries", args=[self.business.pk]),
            reverse("owner_bookings", args=[self.business.pk]),
            reverse("owner_reviews", args=[self.business.pk]),
            reverse("owner_analytics", args=[self.business.pk]),
            reverse("owner_advertisements", args=[self.business.pk]),
            reverse("owner_subscriptions", args=[self.business.pk]),
            reverse("business_verification"),
            reverse("claim_business"),
            reverse("owner_settings"),
        )
        for url in page_urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertContains(
            self.client.get(reverse("owner_enquiries", args=[self.business.pk])),
            enquiry.customer_name,
        )
        self.assertContains(
            self.client.get(reverse("claim_business")),
            unclaimed.name,
        )


class MarketplaceTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name="Bondo Crafts",
            contact_name="Amina",
            location="Bondo",
            phone="0700123456",
            is_published=True,
        )
        self.category = MarketplaceCategory.objects.create(
            name="Home Decor", slug="home-decor"
        )
        self.product = MarketplaceListing.objects.create(
            business=self.business,
            category=self.category,
            name="Woven basket",
            listing_type=MarketplaceListing.PRODUCT,
            description="Handwoven local basket.",
            price="1250.00",
            is_published=True,
        )
        self.service = MarketplaceListing.objects.create(
            business=self.business,
            category=self.category,
            name="Custom weaving",
            listing_type=MarketplaceListing.SERVICE,
            description="Custom baskets made to order.",
            is_published=True,
        )

    def test_marketplace_shows_products_services_prices_and_seller(self):
        response = self.client.get(reverse("marketplace"))

        self.assertContains(response, "Woven basket")
        self.assertContains(response, "Custom weaving")
        self.assertContains(response, "KSh 1250.00")
        self.assertContains(response, "Amina")
        self.assertContains(response, "Home Decor")

    def test_marketplace_filters_by_search_type_location_and_price(self):
        response = self.client.get(
            reverse("marketplace"),
            {
                "q": "basket",
                "listing_type": MarketplaceListing.PRODUCT,
                "location": "Bondo",
                "min_price": "1000",
                "max_price": "1500",
            },
        )

        self.assertContains(response, "Woven basket")
        self.assertNotContains(response, "Custom weaving")

    def test_marketplace_sorting_and_pagination_preserve_filters(self):
        for index in range(12):
            MarketplaceListing.objects.create(
                business=self.business,
                category=self.category,
                name=f"Basket {index:02}",
                description="Another handwoven basket.",
                price=str(100 + index),
                is_published=True,
            )

        response = self.client.get(
            reverse("marketplace"),
            {"q": "basket", "sort": "price_asc", "page": "2"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["result_count"], 14)
        self.assertIn("q=basket", response.context["pagination_query"])
        self.assertIn("sort=price_asc", response.context["pagination_query"])

    def test_marketplace_detail_shows_description_and_seller(self):
        response = self.client.get(
            reverse("marketplace_listing_detail", args=[self.product.pk])
        )

        self.assertContains(response, "Handwoven local basket.")
        self.assertContains(response, "Bondo Crafts")
        self.assertContains(response, reverse("marketplace_enquiry", args=[self.product.pk]))

    def test_marketplace_enquiry_is_saved_for_listing(self):
        response = self.client.post(
            reverse("marketplace_enquiry", args=[self.product.pk]),
            {
                "customer_name": "Local customer",
                "email": "customer@example.com",
                "phone": "0700000000",
                "enquiry_type": MarketplaceEnquiry.ORDER_REQUEST,
                "message": "I would like to order one.",
            },
        )

        self.assertRedirects(response, f"{reverse('marketplace')}#listing-{self.product.pk}")
        enquiry = MarketplaceEnquiry.objects.get()
        self.assertEqual(enquiry.listing, self.product)
        self.assertEqual(enquiry.enquiry_type, MarketplaceEnquiry.ORDER_REQUEST)

    def test_service_enquiry_form_does_not_accept_order_request(self):
        response = self.client.post(
            reverse("marketplace_enquiry", args=[self.service.pk]),
            {
                "customer_name": "Local customer",
                "email": "customer@example.com",
                "enquiry_type": MarketplaceEnquiry.ORDER_REQUEST,
                "message": "Please place an order.",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(MarketplaceEnquiry.objects.exists())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class PlatformGrowthWorkflowTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.owner = self.user_model.objects.create_user(
            username="platform-owner",
            email="platform-owner@example.com",
            password="MtaaBiz-StrongPass-2026!",
            first_name="Platform",
            last_name="Owner",
        )
        self.customer = self.user_model.objects.create_user(
            username="platform-customer",
            email="platform-customer@example.com",
            password="MtaaBiz-CustomerPass-2026!",
            first_name="Local",
            last_name="Customer",
        )
        self.business = Business.objects.create(
            name="Bondo Repair Shop",
            owner=self.owner,
            location="Bondo",
            county="Siaya",
            town="Bondo",
            phone="0700123456",
            latitude="0.023000",
            longitude="37.900000",
            is_published=True,
        )
        self.product = MarketplaceListing.objects.create(
            business=self.business,
            name="Phone accessories",
            listing_type=MarketplaceListing.PRODUCT,
            description="Chargers and cases.",
            is_published=True,
        )
        self.service = MarketplaceListing.objects.create(
            business=self.business,
            name="Phone repair",
            listing_type=MarketplaceListing.SERVICE,
            description="Screen and battery repair.",
            is_published=True,
        )

    def test_customer_account_saves_business_activity_reviews_and_reports(self):
        self.client.force_login(self.customer)
        detail_url = reverse("business_detail", args=[self.business.pk])
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        self.client.post(reverse("toggle_business_favorite", args=[self.business.pk]))
        response = self.client.post(
            reverse("marketplace_enquiry", args=[self.product.pk]),
            {
                "customer_name": "Local Customer",
                "email": "platform-customer@example.com",
                "enquiry_type": MarketplaceEnquiry.ORDER_REQUEST,
                "message": "Please reserve a charger.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.client.post(
            reverse("business_review", args=[self.business.pk]),
            {"rating": "4", "title": "Helpful service", "body": "The repair was quick."},
        )
        self.client.post(
            reverse("business_report", args=[self.business.pk]),
            {"reason": BusinessReport.WRONG_INFORMATION, "details": "Please verify the opening hours."},
        )

        self.assertTrue(FavoriteBusiness.objects.filter(user=self.customer, business=self.business).exists())
        self.assertTrue(RecentlyViewedBusiness.objects.filter(user=self.customer, business=self.business).exists())
        self.assertTrue(BusinessEvent.objects.filter(business=self.business, event_type=BusinessEvent.PROFILE_VIEW).exists())
        enquiry = MarketplaceEnquiry.objects.get()
        self.assertEqual(enquiry.customer, self.customer)
        self.assertEqual(enquiry.enquiry_type, MarketplaceEnquiry.ORDER_REQUEST)
        review = BusinessReview.objects.get()
        self.assertFalse(review.is_approved)
        self.assertEqual(BusinessReport.objects.get().reporter, self.customer)

        dashboard = self.client.get(reverse("customer_dashboard"))
        self.assertContains(dashboard, "My orders")
        self.assertContains(dashboard, "Bondo Repair Shop")
        self.assertEqual(self.client.get(reverse("customer_settings")).status_code, 200)

        self.client.post(
            reverse("customer_settings"),
            {"action": "notifications"},
        )
        self.assertFalse(UserNotificationPreference.objects.get(user=self.customer).in_app_enabled)
        notify_user(self.customer, "This notification should be muted.", reverse("customer_dashboard"))
        self.assertFalse(UserNotification.objects.filter(user=self.customer).exists())

    def test_service_booking_owner_response_and_customer_cancellation(self):
        self.client.force_login(self.customer)
        appointment = timezone.localtime(timezone.now() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")
        response = self.client.post(
            reverse("service_booking", args=[self.service.pk]),
            {"appointment_at": appointment, "message": "After 3 pm if possible."},
        )
        self.assertRedirects(response, reverse("business_detail", args=[self.business.pk]))
        booking = ServiceBooking.objects.get()
        self.assertEqual(booking.customer, self.customer)
        self.assertTrue(UserNotification.objects.filter(user=self.owner, message__icontains="booking").exists())

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("owner_booking_update", args=[booking.pk]),
            {"status": ServiceBooking.CONFIRMED},
        )
        self.assertRedirects(response, reverse("owner_bookings", args=[self.business.pk]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, ServiceBooking.CONFIRMED)
        self.assertTrue(UserNotification.objects.filter(user=self.customer, message__icontains="booking").exists())

        self.client.force_login(self.customer)
        response = self.client.post(reverse("customer_booking_cancel", args=[booking.pk]))
        self.assertRedirects(response, reverse("customer_dashboard"))
        booking.refresh_from_db()
        self.assertEqual(booking.status, ServiceBooking.CANCELLED)

    def test_review_moderation_rating_and_owner_reply(self):
        self.client.force_login(self.customer)
        self.client.post(
            reverse("business_review", args=[self.business.pk]),
            {"rating": "4", "title": "Helpful service", "body": "The repair was quick."},
        )
        review = BusinessReview.objects.get()
        review_admin = BusinessReviewAdmin(BusinessReview, admin.site)
        with patch.object(review_admin, "message_user"):
            review_admin.approve_reviews(
                None,
                BusinessReview.objects.filter(pk=review.pk),
            )

        self.business.refresh_from_db()
        self.assertEqual(str(self.business.rating), "4.0")
        self.assertEqual(self.business.review_count, 1)
        review.refresh_from_db()
        self.assertTrue(review.is_approved)

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("owner_review_reply", args=[review.pk]),
            {"owner_response": "Thank you for your feedback."},
        )
        self.assertRedirects(response, reverse("owner_reviews", args=[self.business.pk]))
        review.refresh_from_db()
        self.assertEqual(review.owner_response, "Thank you for your feedback.")

    def test_location_assistant_articles_and_whatsapp_contact_tracking(self):
        response = self.client.get(
            reverse("nearby_businesses"),
            {"lat": "0.023", "lng": "37.9", "radius": "5"},
        )
        self.assertContains(response, self.business.name)
        self.assertContains(response, "km away")

        response = self.client.get(reverse("business_assistant"), {"q": "phone repair Bondo"})
        self.assertContains(response, self.business.name)

        response = self.client.get(
            reverse("track_business_contact", args=[self.business.pk, "whatsapp"])
        )
        self.assertEqual(response["Location"], "https://wa.me/254700123456")
        self.assertTrue(BusinessEvent.objects.filter(event_type=BusinessEvent.WHATSAPP_CLICK).exists())

        article = ContentArticle.objects.create(
            title="Reach customers online",
            slug="reach-customers-online",
            summary="A short marketing guide.",
            body="Keep your hours and contact details current.",
            content_type=ContentArticle.RESOURCE,
            is_published=True,
            published_at=timezone.now(),
        )
        self.assertContains(self.client.get(reverse("business_hub")), article.title)
        self.assertContains(
            self.client.get(reverse("resource_detail", args=[article.slug])),
            article.body,
        )
        blog_article = ContentArticle.objects.create(
            title="Stories from local business",
            slug="local-business-stories",
            summary="Local business news.",
            body="A community success story.",
            content_type=ContentArticle.BLOG,
            is_published=True,
            published_at=timezone.now(),
        )
        self.assertContains(self.client.get(reverse("blog")), blog_article.title)

    def test_manual_subscription_payment_and_admin_reports(self):
        plan = ListingPlan.objects.create(
            name="Growth package",
            description="A managed package.",
            amount="1200.00",
            billing_period=ListingPlan.MONTHLY,
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("owner_subscriptions", args=[self.business.pk]),
            {"plan": plan.pk},
        )
        self.assertRedirects(response, reverse("owner_subscriptions", args=[self.business.pk]))
        subscription = SubscriptionRequest.objects.get(business=self.business, plan=plan)
        self.assertEqual(subscription.status, SubscriptionRequest.AWAITING_PAYMENT)

        response = self.client.post(
            reverse("owner_manual_payment", args=["subscription", subscription.pk]),
            {"method": ManualPayment.MPESA, "reference": "MPESA-PLATFORM-001"},
        )
        self.assertRedirects(response, reverse("owner_subscriptions", args=[self.business.pk]))
        payment = ManualPayment.objects.get()
        self.assertEqual(payment.amount, Decimal("1200.00"))
        self.assertEqual(payment.status, ManualPayment.SUBMITTED)

        self.client.post(
            reverse("owner_advertisements", args=[self.business.pk]),
            {
                "title": "Summer campaign",
                "placement": AdvertisementCampaign.DIRECTORY,
                "starts_on": "",
                "ends_on": "",
                "notes": "Promote our repair service.",
            },
        )
        campaign = AdvertisementCampaign.objects.get(business=self.business)
        campaign.status = AdvertisementCampaign.AWAITING_PAYMENT
        campaign.amount_due = Decimal("600.00")
        campaign.save(update_fields=("status", "amount_due"))
        self.client.post(
            reverse("owner_manual_payment", args=["advertisement", campaign.pk]),
            {"method": ManualPayment.MPESA, "reference": "MPESA-PLATFORM-002"},
        )

        admin_user = self.user_model.objects.create_superuser(
            username="platform-admin",
            email="platform-admin@example.com",
            password="MtaaBiz-AdminPass-2026!",
        )
        self.client.force_login(admin_user)
        payment_admin = ManualPaymentAdmin(ManualPayment, admin.site)
        with patch.object(payment_admin, "message_user"):
            payment_admin.confirm_payments(None, ManualPayment.objects.all())
        subscription.refresh_from_db()
        payment.refresh_from_db()
        campaign.refresh_from_db()
        self.assertEqual(subscription.status, SubscriptionRequest.ACTIVE)
        self.assertEqual(payment.status, ManualPayment.CONFIRMED)
        self.assertEqual(campaign.status, AdvertisementCampaign.ACTIVE)

        self.assertEqual(self.client.get(reverse("admin_reports")).status_code, 200)
        csv_response = self.client.get(reverse("admin_revenue_csv"))
        self.assertContains(csv_response, "MPESA-PLATFORM-001")
        self.assertContains(csv_response, "MPESA-PLATFORM-002")


class SuperuserRegistrationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_superuser_logs_in_via_login_form_and_reaches_admin_dashboard(self):
        self.user_model.objects.create_superuser(
            username="admin-user",
            email="admin-user@example.com",
            password="MtaaBiz-NewStrongPass-2026!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "admin-user",
                "password": "MtaaBiz-NewStrongPass-2026!",
            },
        )

        self.assertRedirects(response, reverse("admin_reports"))
        self.assertTrue(self.client.session.get("_auth_user_id"))

    def test_successful_login_is_tracked_for_admin_reports(self):
        self.user_model.objects.create_user(
            username="tracked-user",
            email="tracked-user@example.com",
            password="MtaaBiz-NewStrongPass-2026!",
        )
        UserLoginEvent.objects.all().delete()
        self.client.post(
            reverse("login"),
            {
                "username": "tracked-user",
                "password": "MtaaBiz-NewStrongPass-2026!",
            },
        )

        event = UserLoginEvent.objects.get(user__username="tracked-user")
        self.assertEqual(event.method, UserLoginEvent.METHOD_PASSWORD)

        admin = self.user_model.objects.create_superuser(
            username="reports-admin",
            email="reports-admin@example.com",
            password="MtaaBiz-AdminPass-2026!",
        )
        self.client.force_login(admin)
        response = self.client.get(reverse("admin_reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tracked-user")
        self.assertContains(response, "Recent user logins")

    def test_normal_signup_does_not_get_staff_rights(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "normal-user",
                "first_name": "Normal",
                "last_name": "User",
                "email": "normal-user@example.com",
                "password1": "MtaaBiz-NewStrongPass-2026!",
                "password2": "MtaaBiz-NewStrongPass-2026!",
            },
        )

        self.assertRedirects(response, reverse("login"))
        user = self.user_model.objects.get(username="normal-user")
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
