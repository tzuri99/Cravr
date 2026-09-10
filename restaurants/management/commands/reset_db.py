from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Resets the database, cleans migrations, creates admin, and seeds restaurant data."

    def handle(self, *args, **options):
        # 1. Automatically clean up the migrations folder (keeping __init__.py)
        migrations_dir = Path(settings.BASE_DIR) / "restaurants" / "migrations"
        if migrations_dir.exists():
            for file in migrations_dir.iterdir():
                if file.is_file() and file.name != "__init__.py":
                    file.unlink()
                    self.stdout.write(self.style.WARNING(f"Deleted migration file: {file.name}"))

        # 2. Automatically delete the old db.sqlite3 database file
        db_path = Path(settings.BASE_DIR) / "db.sqlite3"
        if db_path.exists():
            db_path.unlink()
            self.stdout.write(self.style.WARNING("Deleted db.sqlite3"))

        # 3. Re-creating clean migrations...
        self.stdout.write(self.style.SUCCESS("Re-creating clean migrations..."))
        call_command("makemigrations")
        call_command("migrate")

        # 💡 3.5. Automatically recreate the super administrator account.
        self.stdout.write(self.style.SUCCESS("Creating default admin user..."))
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='Vincent',
                email='vngoi0327@gmail.com',
                password='@Vin07cent'
            )
            self.stdout.write(self.style.SUCCESS("Created Admin: Vincent | Password: @Vin07cent"))

        # 4. Automatically seed the database with initial restaurant data
        self.stdout.write(self.style.SUCCESS("Seeding database with initial restaurant data..."))
        call_command("seed_restaurants")

        self.stdout.write(self.style.SUCCESS("Database has been successfully reset and seeded!"))