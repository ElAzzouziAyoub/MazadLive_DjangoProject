from django.db import migrations


DEFAULT_CATEGORIES = [
    'Electronics',
    'Vehicles',
    'Jewelry & Watches',
    'Art & Collectibles',
    'Clothing & Accessories',
    'Books & Music',
    'Furniture & Home',
    'Sports & Outdoors',
    'Real Estate',
    'Other',
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model('auctions', 'Category')
    from django.utils.text import slugify
    for name in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(name=name, defaults={'slug': slugify(name)})


def unseed_categories(apps, schema_editor):
    Category = apps.get_model('auctions', 'Category')
    Category.objects.filter(name__in=DEFAULT_CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('auctions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_categories, reverse_code=unseed_categories),
    ]
