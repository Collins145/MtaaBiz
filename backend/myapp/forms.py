from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import (
    AdvertisementCampaign,
    Business,
    BusinessClaim,
    BusinessReport,
    BusinessReview,
    BusinessVerificationRequest,
    Category,
    Contact,
    ManualPayment,
    MarketplaceCategory,
    MarketplaceEnquiry,
    MarketplaceListing,
    Promotion,
    ServiceBooking,
    UserNotificationPreference,
)


class AccountRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class OwnerAccountForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email")
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account is already using this email.")
        return email


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ("name", "email", "subject", "message")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class BusinessSubmissionForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = (
            "name",
            "category",
            "contact_name",
            "phone",
            "email",
            "county",
            "town",
            "physical_address",
            "latitude",
            "longitude",
            "description",
            "offerings",
            "logo_url",
            "cover_image_url",
            "opening_hours",
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "x_url",
            "linkedin_url",
            "website_url",
        )
        labels = {
            "name": "Business name",
            "category": "Business category",
            "contact_name": "Owner's name",
            "phone": "Phone number",
            "email": "Business email",
            "county": "County",
            "town": "Town",
            "physical_address": "Physical address",
            "latitude": "Map latitude (optional)",
            "longitude": "Map longitude (optional)",
            "description": "Business description",
            "offerings": "Products and services",
            "logo_url": "Business logo URL (optional)",
            "cover_image_url": "Cover photo URL (optional)",
            "opening_hours": "Business opening hours (optional)",
            "facebook_url": "Facebook page URL (optional)",
            "instagram_url": "Instagram profile URL (optional)",
            "tiktok_url": "TikTok profile URL (optional)",
            "x_url": "X profile URL (optional)",
            "linkedin_url": "LinkedIn page URL (optional)",
            "website_url": "Website URL (optional)",
        }
        help_texts = {
            "logo_url": "Paste a public link to your business logo.",
            "cover_image_url": "Paste a public link to a wide photo of your business.",
            "latitude": "Map coordinates help customers find nearby businesses. You can leave these blank.",
            "longitude": "Map coordinates help customers find nearby businesses. You can leave these blank.",
            "opening_hours": "Enter your usual days and hours, including any closed days.",
            "facebook_url": "Paste a full link to your business page.",
            "instagram_url": "Paste a full link to your business profile.",
            "tiktok_url": "Paste a full link to your business profile.",
            "x_url": "Paste a full link to your business profile.",
            "linkedin_url": "Paste a full link to your business page.",
            "website_url": "Paste your website link, if your business has one.",
        }
        widgets = {
            "contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "county": forms.TextInput(attrs={"class": "form-control"}),
            "town": forms.TextInput(attrs={"class": "form-control"}),
            "physical_address": forms.TextInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.000001", "placeholder": "-90 to 90"}
            ),
            "longitude": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.000001", "placeholder": "-180 to 180"}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "offerings": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "logo_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com/business-logo.png",
                }
            ),
            "cover_image_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://example.com/business-cover-photo.jpg",
                }
            ),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "opening_hours": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "e.g. Mon-Sat, 8:00 AM-6:00 PM",
                }
            ),
            "facebook_url": forms.URLInput(attrs={"class": "form-control"}),
            "instagram_url": forms.URLInput(attrs={"class": "form-control"}),
            "tiktok_url": forms.URLInput(attrs={"class": "form-control"}),
            "x_url": forms.URLInput(attrs={"class": "form-control"}),
            "linkedin_url": forms.URLInput(attrs={"class": "form-control"}),
            "website_url": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://example.com"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        for field_name in (
            "category",
            "contact_name",
            "phone",
            "email",
            "county",
            "town",
            "physical_address",
            "description",
            "offerings",
        ):
            self.fields[field_name].required = True

    def save(self, commit=True):
        business = super().save(commit=False)
        business.location = self.cleaned_data["town"]
        business.image_url = (
            self.cleaned_data.get("cover_image_url") or business.image_url
        )
        if commit:
            business.save()
            self.save_m2m()
        return business

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")
        if (latitude is None) != (longitude is None):
            self.add_error("longitude", "Enter both map coordinates, or leave both blank.")
        return cleaned_data


class MarketplaceListingForm(forms.ModelForm):
    price = forms.DecimalField(
        label="Price (KSh)",
        required=False,
        min_value=0,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": "0", "step": "0.01"}
        ),
    )

    class Meta:
        model = MarketplaceListing
        fields = (
            "name",
            "category",
            "listing_type",
            "description",
            "image_url",
            "price",
            "is_available",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "listing_type": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "image_url": forms.URLInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = MarketplaceCategory.objects.filter(is_active=True)
        self.fields["category"].required = False


class OwnerPromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ("title", "description", "starts_on", "ends_on")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "starts_on": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ends_on": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        starts_on = cleaned_data.get("starts_on")
        ends_on = cleaned_data.get("ends_on")
        if starts_on and ends_on and ends_on < starts_on:
            self.add_error("ends_on", "The end date must be on or after the start date.")
        return cleaned_data


class EnquiryStatusForm(forms.ModelForm):
    class Meta:
        model = MarketplaceEnquiry
        fields = ("status",)
        widgets = {"status": forms.Select(attrs={"class": "form-select"})}


class BusinessVerificationForm(forms.ModelForm):
    class Meta:
        model = BusinessVerificationRequest
        fields = (
            "business",
            "registration_number",
            "contact_name",
            "phone",
            "email",
            "notes",
        )
        widgets = {
            "business": forms.Select(attrs={"class": "form-select"}),
            "registration_number": forms.TextInput(attrs={"class": "form-control"}),
            "contact_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "autocomplete": "tel"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["business"].queryset = businesses = Business.objects.filter(
            owner=user
        ).order_by("name")
        if not self.is_bound and businesses.count() == 1:
            business = businesses.first()
            self.initial.setdefault("business", business.pk)
            self.initial.setdefault("contact_name", business.contact_name)
            self.initial.setdefault("phone", business.phone)
            self.initial.setdefault("email", business.email)


class BusinessClaimForm(forms.ModelForm):
    class Meta:
        model = BusinessClaim
        fields = ("business", "email", "phone", "message")
        widgets = {
            "business": forms.Select(attrs={"class": "form-select"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "form-control", "autocomplete": "tel"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["business"].queryset = Business.objects.filter(
            is_published=True, owner__isnull=True
        ).order_by("name")
        if not self.is_bound:
            self.initial.setdefault("email", user.email)

    def clean_business(self):
        business = self.cleaned_data["business"]
        if BusinessClaim.objects.filter(
            business=business,
            user=self.user,
            status=BusinessClaim.PENDING,
        ).exists():
            raise forms.ValidationError("You already have a claim awaiting review for this business.")
        return business


class NewsletterForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "id": "newsletter-email",
                "placeholder": "Your email address",
                "aria-label": "Your email address",
            }
        )
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class MarketplaceFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Products, services or sellers"}),
    )
    category = forms.ModelChoiceField(
        queryset=MarketplaceCategory.objects.none(),
        required=False,
        empty_label="All categories",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    listing_type = forms.ChoiceField(
        required=False,
        choices=(("", "Products and services"),) + MarketplaceListing.LISTING_TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sort = forms.ChoiceField(
        required=False,
        label="Sort by",
        choices=(
            ("newest", "Newest"),
            ("price_asc", "Price: low to high"),
            ("price_desc", "Price: high to low"),
            ("name", "Name"),
        ),
        initial="newest",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.CharField(
        required=False,
        label="Location",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Town or neighborhood"}),
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Minimum price (KSh)",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Maximum price (KSh)",
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = MarketplaceCategory.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        minimum = cleaned_data.get("min_price")
        maximum = cleaned_data.get("max_price")
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error("max_price", "Maximum price must be greater than or equal to minimum price.")
        return cleaned_data


class MarketplaceEnquiryForm(forms.ModelForm):
    class Meta:
        model = MarketplaceEnquiry
        fields = ("customer_name", "email", "phone", "enquiry_type", "message")
        widgets = {
            "customer_name": forms.TextInput(attrs={"class": "form-control", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
            "phone": forms.TelInput(attrs={"class": "form-control", "autocomplete": "tel"}),
            "enquiry_type": forms.Select(attrs={"class": "form-select"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, listing, **kwargs):
        super().__init__(*args, **kwargs)
        self.listing = listing
        if listing.listing_type == MarketplaceListing.SERVICE:
            self.fields["enquiry_type"].choices = (
                (MarketplaceEnquiry.ENQUIRY, "General enquiry"),
                (MarketplaceEnquiry.QUOTE_REQUEST, "Request a quote"),
            )
            self.fields["enquiry_type"].initial = MarketplaceEnquiry.QUOTE_REQUEST
        else:
            self.fields["enquiry_type"].choices = (
                (MarketplaceEnquiry.ENQUIRY, "General enquiry"),
                (MarketplaceEnquiry.ORDER_REQUEST, "Order request"),
            )
            self.fields["enquiry_type"].initial = MarketplaceEnquiry.ORDER_REQUEST

    def clean_enquiry_type(self):
        enquiry_type = self.cleaned_data["enquiry_type"]
        allowed_types = {choice[0] for choice in self.fields["enquiry_type"].choices}
        if enquiry_type not in allowed_types:
            raise forms.ValidationError("Choose an enquiry option available for this listing.")
        return enquiry_type


class ServiceBookingForm(forms.ModelForm):
    class Meta:
        model = ServiceBooking
        fields = ("appointment_at", "message")
        widgets = {
            "appointment_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "message": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Anything the provider should know?"}
            ),
        }

    def clean_appointment_at(self):
        appointment_at = self.cleaned_data["appointment_at"]
        if appointment_at <= timezone.now():
            raise forms.ValidationError("Choose a date and time in the future.")
        return appointment_at


class BusinessReviewForm(forms.ModelForm):
    class Meta:
        model = BusinessReview
        fields = ("rating", "title", "body")
        widgets = {
            "rating": forms.Select(
                attrs={"class": "form-select"},
                choices=((value, f"{value} star{'s' if value != 1 else ''}") for value in range(1, 6)),
            ),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class BusinessReviewResponseForm(forms.ModelForm):
    class Meta:
        model = BusinessReview
        fields = ("owner_response",)
        widgets = {
            "owner_response": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Write a response to this review"}
            )
        }


class BookingStatusForm(forms.ModelForm):
    class Meta:
        model = ServiceBooking
        fields = ("status",)
        widgets = {"status": forms.Select(attrs={"class": "form-select"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = {
            ServiceBooking.PENDING: (
                (ServiceBooking.CONFIRMED, "Confirmed"),
                (ServiceBooking.DECLINED, "Declined"),
            ),
            ServiceBooking.CONFIRMED: (
                (ServiceBooking.DECLINED, "Declined"),
                (ServiceBooking.COMPLETED, "Completed"),
            ),
        }
        self.fields["status"].choices = choices.get(self.instance.status, ())


class AdvertisementCampaignForm(forms.ModelForm):
    class Meta:
        model = AdvertisementCampaign
        fields = ("title", "placement", "starts_on", "ends_on", "notes")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "placement": forms.Select(attrs={"class": "form-select"}),
            "starts_on": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "ends_on": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        starts_on = cleaned_data.get("starts_on")
        ends_on = cleaned_data.get("ends_on")
        if starts_on and ends_on and ends_on < starts_on:
            self.add_error("ends_on", "The end date must be on or after the start date.")
        return cleaned_data


class ManualPaymentSubmissionForm(forms.ModelForm):
    class Meta:
        model = ManualPayment
        fields = ("method", "reference")
        widgets = {
            "method": forms.Select(attrs={"class": "form-select"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
        }


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserNotificationPreference
        fields = ("in_app_enabled",)
        labels = {"in_app_enabled": "Receive in-app updates"}
        widgets = {"in_app_enabled": forms.CheckboxInput(attrs={"class": "form-check-input"})}


class BusinessReportForm(forms.ModelForm):
    class Meta:
        model = BusinessReport
        fields = ("reason", "details")
        widgets = {
            "reason": forms.Select(attrs={"class": "form-select"}),
            "details": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Tell us what should be reviewed."}
            ),
        }
