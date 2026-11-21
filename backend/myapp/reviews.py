from django.db.models import Avg, Count

from .models import Business, BusinessReview


def refresh_business_rating(business_id):
    ratings = BusinessReview.objects.filter(
        business_id=business_id, is_approved=True
    ).aggregate(average=Avg("rating"), count=Count("pk"))
    Business.objects.filter(pk=business_id).update(
        rating=ratings["average"] or 0,
        review_count=ratings["count"],
    )
