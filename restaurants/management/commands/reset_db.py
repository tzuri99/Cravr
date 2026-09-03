import os
from pathlib import Path
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Resets local database, creates new migrations, and seeds initial data."

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES['default']['NAME'])
        
        # 1. Delete the old database
        if db_path.exists():
            os.remove(db_path)
            self.stdout.write(self.style.SUCCESS("Deleted old db.sqlite3"))

        # 2. Regenerate migration files
        self.stdout.write("Making migrations...")
        call_command("makemigrations")

        # 3. Run migrations
        self.stdout.write("Running migrations...")
        call_command("migrate")

        # 4. Run seeding
        self.stdout.write("Seeding data...")
        call_command("seed_restaurants")

        self.stdout.write(self.style.SUCCESS("Database successfully reset and seeded!"))