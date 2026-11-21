"""Sitemaps for SEO: static pages, published businesses, blog and resource articles."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Business, ContentArticle


class StaticViewSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return ["index", "about", "businesses", "deals", "blog", "business_hub", "marketplace", "pricing", "contact"]

    def location(self, item):
        return reverse(item)


class BusinessSitemap(Sitemap):
    priority = 0.9
    changefreq = "daily"

    def items(self):
        return Business.objects.filter(is_published=True)

    def location(self, obj):
        return obj.get_absolute_url()

    def lastmod(self, obj):
        return obj.created_at


class ArticleSitemap(Sitemap):
    priority = 0.6
    changefreq = "weekly"

    def items(self):
        return ContentArticle.objects.filter(is_published=True)

    def location(self, obj):
        if obj.content_type == ContentArticle.RESOURCE:
            return reverse("resource_detail", args=[obj.slug])
        return reverse("article_detail", args=[obj.slug])

    def lastmod(self, obj):
        return obj.published_at or obj.created_at


sitemaps = {
    "static": StaticViewSitemap,
    "businesses": BusinessSitemap,
    "articles": ArticleSitemap,
}
