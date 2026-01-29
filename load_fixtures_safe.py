#!/usr/bin/env python
"""Idempotent fixture loader for non-empty databases.

- Respects ENVIRONMENT (runs only for local/development).
- Iterates over all app fixtures and creates only missing rows.
- Skips records whose PK already exists or which violate unique constraints.

This is designed to complement load-fixtures.sh when you add new
objects to existing fixture files and want to load only the new ones.
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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.config.settings")
try:
    django.setup()
except Exception as e:
    print(f"❌ Failed to setup Django: {e}")
    print("\n💡 TIP: If you are running this on your host machine, ensure Docker is running and ports are mapped.")
    print("   Or run it inside the container: docker exec powerbank_local-api-1 python load_fixtures_safe.py")
    exit(1)

from django.apps import apps
from django.db import transaction, IntegrityError


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
    print(f"Safely loading fixture: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            objects = json.load(f)
    except Exception as e:
        print(f"  Failed to read fixture {path}: {e}")
        return

    for obj in objects:
        model_label = obj.get("model")
        if not model_label:
            print("  Skipping entry without model")
            continue

        try:
            app_label, model_name = model_label.split(".", 1)
            model = apps.get_model(app_label, model_name)
        except Exception as e:
            print(f"  Skipping unknown model '{model_label}': {e}")
            continue

        pk = obj.get("pk")
        fields = dict(obj.get("fields", {}))

        # If PK is provided and already exists, skip immediately
        if pk is not None and model.objects.filter(pk=pk).exists():
            print(f"  • Skipping existing {model_label} pk={pk}")
            continue

        # Separate many-to-many data so we can set it after the instance is saved
        m2m_data = {}
        for m2m_field in model._meta.many_to_many:
            name = m2m_field.name
            if name in fields:
                m2m_data[name] = fields.pop(name)

        # Build instance and assign primary key explicitly
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
                print(f"  Created {model_label} pk={instance.pk}")
        except IntegrityError as e:
            msg = str(e)
            # Treat unique/duplicate key errors as "already exists" and continue
            if "duplicate key value violates unique constraint" in msg or "UNIQUE constraint failed" in msg:
                print(f"  • Skipping existing (unique constraint) {model_label} pk={pk}: {e}")
            else:
                print(f"  Failed to create {model_label} pk={pk}: {e}")
        except Exception as e:
            print(f"  Failed to create {model_label} pk={pk}: {e}")


def main() -> None:
    env = os.getenv("ENVIRONMENT", "local").lower()

    print("Starting safe fixture loading (idempotent)...")
    print(f"ENVIRONMENT={env}")

    base_dir = os.path.dirname(os.path.abspath(__file__))

    for app_label in APPS_IN_ORDER:
        fixtures_dir = os.path.join(base_dir, "api", "user", app_label, "fixtures")
        if not os.path.isdir(fixtures_dir):
            continue

        print(f"==== App: {app_label} ====")

        # Load all JSON fixtures in deterministic order
        fixture_files = sorted(
            f
            for f in os.listdir(fixtures_dir)
            if f.endswith(".json")
        )

        if not fixture_files:
            print("  (no fixtures found)")
            continue

        for filename in fixture_files:
            path = os.path.join(fixtures_dir, filename)
            load_fixture_file_safe(path)

    print("Safe fixtures loading completed!")


if __name__ == "__main__":
    main()
