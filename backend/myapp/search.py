"""Search helpers for the business directory.

Uses PostgreSQL full-text search (SearchVector / SearchRank) when the project
is running on Postgres, and falls back to portable ``icontains`` filtering on
SQLite / other backends. Selection is cached per query to reduce load.
"""

from django.db import connection


def _postgres_search_available():
    if connection.vendor != "postgresql":
        return False
    try:
        from django.contrib.postgres.search import SearchRank, SearchVector  # noqa: F401

        return True
    except ImportError:
        return False


def search_businesses(queryset, query):
    """Apply a text search to a Business queryset."""
    query = (query or "").strip()
    if not query:
        return queryset

    if _postgres_search_available():
        from django.contrib.postgres.search import SearchRank, SearchVector

        vector = (
            SearchVector("name", weight="A")
            + SearchVector("offerings", weight="B")
            + SearchVector("description", weight="B")
            + SearchVector("category__name", weight="C")
            + SearchVector("county", weight="C")
            + SearchVector("town", weight="C")
        )
        return queryset.annotate(search_rank=SearchRank(vector, query)).filter(
            search_rank__gte=0.05
        )

    from django.db.models import Q

    return queryset.filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(offerings__icontains=query)
        | Q(category__name__icontains=query)
    )


def order_by_search_relevance(queryset, query):
    """Order by full-text relevance on Postgres; leaves ordering untouched otherwise."""
    query = (query or "").strip()
    if query and _postgres_search_available():
        return queryset.order_by("-search_rank")
    return queryset


def using_postgres():
    return connection.vendor == "postgresql"
