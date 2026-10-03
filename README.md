# Cravr

Cravr is a Django-based restaurant discovery and review web application. It supports restaurant browsing, filtering, maps, wishlists, user profiles, reviews with photo uploads, Google sign-in, OTP email verification, and restaurant submission/approval workflows.

This README explains how to install, configure, and run the project from a downloaded or extracted project folder.

---

## Features

### Restaurants
- Browse approved restaurants
- Search restaurants by name or address
- Filter by cuisine, meal type, dietary information, and tags
- View restaurant details and opening hours
- View restaurants on an interactive Leaflet/OpenStreetMap map
- Open a restaurant directly on the map from its detail page
- Use the Random Restaurant Picker
- Submit new restaurants for approval

### Reviews
- Add 1–5 star ratings
- Write review text
- Upload up to 5 photos per review
- Edit reviews
- Add or remove photos while editing
- Delete reviews
- View all reviews written by the logged-in user from the profile page

### Accounts and Profiles
- Register using username, email, and password
- OTP email verification
- Login and logout
- Remember Me
- Google sign-in
- Forgot-password flow
- Profile picture
- Cover photo
- Bio and privacy settings
- Followers/following
- Follow, unfollow, block, and unblock users

### Wishlist
- Add restaurants to a wishlist
- Remove restaurants from a wishlist
- Use wishlist-related filters in the restaurant picker

---

# Tech Stack

## Backend
- Python
- Django 6.1
- SQLite
- django-allauth
- Google OAuth
- Gmail API

## Frontend
- Django Templates
- HTML
- CSS
- JavaScript
- Leaflet
- Leaflet MarkerCluster
- OpenStreetMap

## Other
- Pillow for image uploads
- python-decouple for environment configuration
- WhiteNoise for deployed static files
- Gunicorn for Railway deployment

---

# Project Structure

A simplified project structure looks like this:

```text
Cravr/
├── accounts/
│   ├── adapter.py
│   ├── gmail_email_backend.py
│   ├── models.py
│   ├── signals.py
│   ├── urls.py
│   └── views.py
│
├── restaurants/
│   ├── management/
│   │   └── commands/
│   ├── forms.py
│   ├── models.py
│   ├── urls.py
│   ├── utils.py
│   └── views.py
│
├── cravr_project/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── templates/
│   ├── accounts/
│   └── restaurants/
│
├── static/
│   └── css/
│       └── style.css
│
├── seed_data/
│   └── restaurants.csv
│
├── data/
│   ├── db.sqlite3
│   └── media/
│
├── manage.py
├── requirements.txt
├── pyproject.toml
├── uv.lock
├── .env
└── README.md
```

---

# Prerequisites

Install Python before running the project.

Check that Python is available:

```bash
python --version
```

On some macOS/Linux systems, use:

```bash
python3 --version
```

The project does not require `uv` to run. Standard Python and `pip` are sufficient.

Internet access is required for:
- Google sign-in
- Gmail API email delivery
- OpenStreetMap tiles

---

# Installation

## 1. Open the project folder

Extract the project ZIP if necessary, then open a terminal inside the folder containing:

```text
manage.py
requirements.txt
pyproject.toml
.env
```

Example:

```bash
cd Cravr
```

---

## 2. Create a virtual environment

Using a virtual environment keeps the project dependencies separate from other Python projects.

### Windows

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

When the environment is active, the terminal normally shows something similar to:

```text
(.venv)
```

---

## 3. Upgrade pip

```bash
python -m pip install --upgrade pip
```

---

## 4. Install dependencies

Run this command from the project root:

```bash
python -m pip install -r requirements.txt
```

The project uses packages including Django, django-allauth, Pillow, python-decouple, Requests, and the libraries required for Google/Gmail integration.

Do not run:

```bash
pip install requirements.txt
```

The `-r` is required because it tells pip to install packages listed inside the file.

---

# Configuration

The project uses a `.env` file in the same directory as `manage.py`.

Example structure:

```text
Cravr/
├── manage.py
├── .env
├── requirements.txt
└── ...
```

The project reads environment variables using `python-decouple`.

A typical `.env` contains:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

GOOGLE_CLIENT_ID=your-google-sign-in-client-id
GOOGLE_CLIENT_SECRET=your-google-sign-in-client-secret

GMAIL_CLIENT_ID=your-gmail-api-client-id
GMAIL_CLIENT_SECRET=your-gmail-api-client-secret
GMAIL_REFRESH_TOKEN=your-gmail-refresh-token
GMAIL_SENDER_EMAIL=your-email@example.com
```

Keep the variable names exactly as shown because the Django settings read these names directly.

---

# Environment Variable Reference

## `SECRET_KEY`

Django secret key:

```env
SECRET_KEY=...
```

This value should not be exposed publicly.

---

## `DEBUG`

For local development:

```env
DEBUG=True
```

For a public deployment:

```env
DEBUG=False
```

---

## Google Sign-In

These variables are used by `django-allauth`:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

They belong to the Google OAuth Web Application used for Google sign-in.

---

## Gmail API

These variables are used to send OTP and account-related emails:

```env
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
GMAIL_SENDER_EMAIL=...
```

The Gmail credentials are separate from the Google sign-in credentials.

---

# Google OAuth Configuration

Google sign-in requires the correct OAuth redirect URI.

For local development using `127.0.0.1`:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

If the project is opened using `localhost`, also configure:

```text
http://localhost:8000/accounts/google/login/callback/
```

Recommended local JavaScript origins:

```text
http://127.0.0.1:8000
http://localhost:8000
```

The exact callback URL, including the trailing slash, must match the Google OAuth configuration.

---

# Gmail API Configuration

Cravr sends OTP verification emails through the Gmail API.

The registration flow is:

```text
Register
   ↓
Create user
   ↓
Generate OTP
   ↓
Send OTP through Gmail API
   ↓
Enter OTP
   ↓
Verify account
   ↓
Login
```

The project also uses Gmail API for account-related email flows such as password reset.

Internet access is required for Gmail API requests.

---

# Database Setup

Cravr uses SQLite.

The database is stored at:

```text
data/db.sqlite3
```

Make sure the `data` folder exists.

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force data
```

### macOS / Linux

```bash
mkdir -p data
```

Apply the database migrations:

```bash
python manage.py migrate
```

If the included database is already fully migrated, Django will report that there are no migrations to apply.

---

# Check the Project

Before starting the web server, run:

```bash
python manage.py check
```

A successful result should look similar to:

```text
System check identified no issues
```

---

# Run the Application

Start the local development server:

```bash
python manage.py runserver
```

Open the application in a browser:

```text
http://127.0.0.1:8000/
```

To stop the server, press:

```text
Ctrl + C
```

---

# Quick Start

After extracting the project, the full Windows setup is:

```powershell
cd Cravr
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

For macOS/Linux:

```bash
cd Cravr
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

Then visit:

```text
http://127.0.0.1:8000/
```

---

# Django Admin

The Django Admin page is available at:

```text
http://127.0.0.1:8000/admin/
```

To create a new administrator account:

```bash
python manage.py createsuperuser
```

Enter a username, email, and password when prompted.

---

# User Profiles

Cravr expects users to have an associated `Profile`.

If an older or manually created account raises:

```text
RelatedObjectDoesNotExist
User has no profile
```

open the Django shell:

```bash
python manage.py shell
```

Then run:

```python
from django.contrib.auth.models import User
from accounts.models import Profile

user = User.objects.get(username="YOUR_USERNAME")
Profile.objects.get_or_create(user=user)
```

Exit the shell:

```python
exit()
```

---

# Restaurant Seed Data

Restaurant seed data is stored at:

```text
seed_data/restaurants.csv
```

To import the seed data:

```bash
python manage.py seed_restaurants
```

The management command reads from:

```python
settings.BASE_DIR / "seed_data" / "restaurants.csv"
```

If seeded restaurants are pending approval and need to be made visible:

```bash
python manage.py shell -c "from restaurants.models import Restaurant; n = Restaurant.objects.filter(is_approved=False, added_by__isnull=True).update(is_approved=True); print('Approved', n)"
```

---

# Reviews and Media

Reviews support:
- 1–5 stars
- Written text
- Up to 5 images

Uploaded media is stored under:

```text
data/media/
```

The relevant settings are:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "data" / "media"
```

Review images are stored under paths such as:

```text
data/media/review_photos/
```

Profile and cover images are also stored under the media directory.

Forms that upload files must use:

```html
enctype="multipart/form-data"
```

---

# Static Files

Source static files are stored under:

```text
static/
```

For example:

```text
static/css/style.css
```

The local Django development server serves these files while `DEBUG=True`.

For deployment, WhiteNoise is used for collected static files.

---

# Map

Cravr uses:
- Leaflet
- Leaflet MarkerCluster
- OpenStreetMap tiles

The map requires an internet connection to load its map tiles.

Restaurant markers display information such as:
- Restaurant name
- Cuisine
- Rating
- Address
- Restaurant detail link
- Directions link

The restaurant detail page can link directly to the selected restaurant's map marker.

---

# Useful Commands

## Run the application

```bash
python manage.py runserver
```

## Check the project

```bash
python manage.py check
```

## Create migrations

```bash
python manage.py makemigrations
```

## Apply migrations

```bash
python manage.py migrate
```

## Show migration status

```bash
python manage.py showmigrations
```

## Preview migration operations

```bash
python manage.py migrate --plan
```

## Open the Django shell

```bash
python manage.py shell
```

## Create an administrator

```bash
python manage.py createsuperuser
```

## Import restaurant seed data

```bash
python manage.py seed_restaurants
```

---

# Troubleshooting

## `requirements.txt` cannot be found

Make sure the terminal is currently inside the project folder.

Run:

### Windows

```powershell
dir
```

### macOS/Linux

```bash
ls
```

The output should include:

```text
requirements.txt
manage.py
pyproject.toml
```

If it does not, change into the correct folder before running:

```bash
python -m pip install -r requirements.txt
```

---

## `No matching distribution found for requirements.txt`

Make sure the command contains `-r`.

Correct:

```bash
python -m pip install -r requirements.txt
```

Incorrect:

```bash
pip install requirements.txt
```

---

## Google login shows `invalid_client`

Check:

```env
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
```

Make sure they are the credentials for the Google OAuth Web Application used for sign-in.

Do not replace them with the Gmail API credential pair.

---

## Google login shows `redirect_uri_mismatch`

Make sure Google OAuth contains the exact local callback:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

If using `localhost`, configure:

```text
http://localhost:8000/accounts/google/login/callback/
```

---

## OTP or email sending fails

Check the Gmail API variables in `.env`:

```env
GMAIL_CLIENT_ID
GMAIL_CLIENT_SECRET
GMAIL_REFRESH_TOKEN
GMAIL_SENDER_EMAIL
```

Also make sure the computer has internet access.

---

## Images do not appear

Check that:

```text
data/media/
```

exists and contains the uploaded image files referenced by the database.

---

## `User has no profile`

Create the missing profile through the Django shell:

```python
from django.contrib.auth.models import User
from accounts.models import Profile

user = User.objects.get(username="YOUR_USERNAME")
Profile.objects.get_or_create(user=user)
```

---

# Deployment

The project can also run on Railway.

The current deployment uses:
- Gunicorn
- WhiteNoise
- SQLite
- Persistent storage for the database and uploaded media
- Environment variables for secrets and Google credentials

The deployed data paths are based on:

```text
data/db.sqlite3
data/media/
```

For local use, Railway is not required.

---

# Final Test

Before distributing the project ZIP:

1. Extract the ZIP into a fresh folder.
2. Open a terminal in the folder containing `manage.py`.
3. Create a new virtual environment.
4. Activate it.
5. Install the dependencies from `requirements.txt`.
6. Run migrations.
7. Run the Django system check.
8. Start the server.
9. Test the main pages and integrations.

The core commands are:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

---

# License

This project was developed for academic coursework.