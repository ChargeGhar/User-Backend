#!/usr/bin/env python
"""
Robust and idempotent fixture loader for PowerBank project.
Handles renamed models, unique constraint violations, and missing apps.
"""
import os
import json
import socket
import django

# Handle host machine vs docker network hostnames
db_host = os.getenv("POSTGRES_HOST")
if db_host == "pgbouncer":
    try:
        socket.gethostbyname("pgbouncer")
    except socket.gaierror:
        # pgbouncer is not resolvable, likely running on host machine
        os.environ["POSTGRES_HOST"] = "localhost"
        # Update DATABASE_URL if it exists and contains pgbouncer
        db_url = os.getenv("DATABASE_URL")
        if db_url and "@pgbouncer" in db_url:
            os.environ["DATABASE_URL"] = db_url.replace("@pgbouncer", "@localhost")

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
try:
    django.setup()
except Exception as e:
    print(f"❌ Failed to setup Django: {e}")
    print("\n💡 TIP: If you are running this on your host machine, ensure Docker is running and ports are mapped.")
    print("   Or run it inside the container: docker exec powerbank_local-api-1 python load_fixtures.py")
    exit(1)

from django.apps import apps
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model

# App loading order (foundational apps first)
APPS_IN_ORDER = [
    "system",
    "common",
    "users",
    "content",
    "stations",
    "rentals",
    "payments",
    "points",
    "promotions",
    "social",
    "notifications",
    "admin",
]

def load_fixture_file_safe(path: str) -> None:
    """Loads a single fixture file object-by-object to skip duplicates gracefully."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            objects = json.load(f)
    except Exception as e:
        print(f"  ⚠️  Failed to read fixture {path}: {e}")
        return

    for obj in objects:
        model_label = obj.get("model")
        if not model_label:
            continue

        try:
            app_label, model_name = model_label.split(".", 1)
            model = apps.get_model(app_label, model_name)
        except Exception as e:
            print(f"  ⚠️  Skipping unknown model '{model_label}': {e}")
            continue

        pk = obj.get("pk")
        fields = dict(obj.get("fields", {}))

        # Check if PK exists
        if pk is not None and model.objects.filter(pk=pk).exists():
            continue

        # Handle Many-to-Many separately
        m2m_data = {}
        for m2m_field in model._meta.many_to_many:
            name = m2m_field.name
            if name in fields:
                m2m_data[name] = fields.pop(name)

        # Build instance
        processed_fields = {}
        for field_name, value in fields.items():
            try:
                field = model._meta.get_field(field_name)
                # If it's a foreign key and we have an ID (int, str, etc. but not a model instance),
                # use the _id suffix so Django's constructor doesn't complain.
                if field.is_relation and not field.many_to_many and value is not None:
                    processed_fields[f"{field.name}_id"] = value
                else:
                    processed_fields[field_name] = value
            except Exception:
                processed_fields[field_name] = value

        instance = model(**processed_fields)
        if pk is not None:
            setattr(instance, model._meta.pk.attname, pk)

        try:
            with transaction.atomic():
                instance.save(force_insert=True)
                for name, value in m2m_data.items():
                    getattr(instance, name).set(value)
        except IntegrityError as e:
            msg = str(e)
            if "duplicate key" in msg.lower() or "unique constraint" in msg.lower():
                # Silently skip unique constraint violations (already exists)
                pass
            else:
                print(f"  ⚠️  Integrity error for {model_label} pk={pk}: {e}")
        except Exception as e:
            print(f"  ⚠️  Failed to create {model_label} pk={pk}: {e}")

def main():
    print("🚀 Starting robust fixture loading...")
    
    # Create/Update superuser
    User = get_user_model()
    username = 'janak'
    email = 'janak@powerbank.com'
    password = '5060'
    
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'is_superuser': True, 'is_staff': True, 'is_active': True}
    )
    if created:
        user.set_password(password)
        user.save()
        print(f"✅ Superuser '{username}' created successfully")
    else:
        print(f"ℹ️  Superuser '{username}' already exists")
    
    # Process apps in order
    for app_label in APPS_IN_ORDER:
        fixtures_dir = f"api/{app_label}/fixtures"
        if os.path.isdir(fixtures_dir):
            print(f"📦 Processing fixtures for {app_label}...")
            
            fixture_files = sorted([f for f in os.listdir(fixtures_dir) if f.endswith(".json")])
            for filename in fixture_files:
                path = os.path.join(fixtures_dir, filename)
                load_fixture_file_safe(path)
                print(f"  ✅ Processed {filename}")
    
    print("🎉 Fixtures loading completed!")

if __name__ == '__main__':
    main()
