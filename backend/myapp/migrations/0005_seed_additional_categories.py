from django.db import migrations


def create_additional_categories(apps, schema_editor):
    Category = apps.get_model("myapp", "Category")
    categories = (
        ("Beauty & Personal Care", "beauty-personal-care", "bi bi-scissors", 8),
        ("Professional Services", "professional-services", "bi bi-briefcase-fill", 9),
        ("Real Estate & Property", "real-estate-property", "bi bi-building", 10),
        ("Automotive Services", "automotive-services", "bi bi-car-front-fill", 11),
        ("Events & Entertainment", "events-entertainment", "bi bi-calendar-event-fill", 12),
    )
    Category.objects.bulk_create(
        [
            Category(name=name, slug=slug, icon_class=icon_class, display_order=order)
            for name, slug, icon_class, order in categories
        ],
        ignore_conflicts=True,
    )


def remove_additional_categories(apps, schema_editor):
    Category = apps.get_model("myapp", "Category")
    Category.objects.filter(
        slug__in=(
            "beauty-personal-care",
            "professional-services",
            "real-estate-property",
            "automotive-services",
            "events-entertainment",
        )
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0004_marketplacecategory_marketplacelisting_and_more"),
    ]

    operations = [
        migrations.RunPython(create_additional_categories, remove_additional_categories),
    ]
