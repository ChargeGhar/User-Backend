import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.config.settings')
django.setup()

from django.db import connection
print(f"Table 'user_points' exists: {'user_points' in connection.introspection.table_names()}")
with connection.cursor() as cursor:
    cursor.execute("SELECT app, name FROM django_migrations WHERE app = 'points'")
    migrations = cursor.fetchall()
    print(f"Migrations for 'points' app: {migrations}")
