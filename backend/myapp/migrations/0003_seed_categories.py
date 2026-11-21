from django.db import migrations


def create_default_categories(apps, schema_editor):
    Category = apps.get_model("myapp", "Category")
    categories = (
        ("Restaurants & Hotels", "restaurants-hotels", "bi bi-cup-hot-fill", 1),
        ("Shopping & Retail", "shopping-retail", "bi bi-bag-fill", 2),
        ("Health & Wellness", "health-wellness", "bi bi-heart-pulse-fill", 3),
        ("Education & Training", "education-training", "bi bi-mortarboard-fill", 4),
        ("Construction & Hardware", "construction-hardware", "bi bi-tools", 5),
        ("Transport & Logistics", "transport-logistics", "bi bi-truck", 6),
        ("Technology & ICT", "technology-ict", "bi bi-laptop", 7),
    )
    Category.objects.bulk_create(
        [
            Category(name=name, slug=slug, icon_class=icon_class, display_order=order)
            for name, slug, icon_class, order in categories
        ],
        ignore_conflicts=True,
    )


def remove_default_categories(apps, schema_editor):
    Category = apps.get_model("myapp", "Category")
    Category.objects.filter(
        slug__in=(
            "restaurants-hotels",
            "shopping-retail",
            "health-wellness",
            "education-training",
            "construction-hardware",
            "transport-logistics",
            "technology-ict",
        )
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0002_category_newslettersubscription_sociallink_and_more"),
    ]

    operations = [
        migrations.RunPython(create_default_categories, remove_default_categories),
    ]
