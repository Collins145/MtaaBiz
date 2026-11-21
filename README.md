# MtaaBiz

MtaaBiz is a business listing platform for connecting customers to businesses around their area (Kenya).

## Features

- Business directory with categories, search (PostgreSQL full-text search in production), location filters and pagination
- Business profiles with slug URLs (`/businesses/12-naivas-kiambu-road/`), Google Maps embed, "Open now" badges and schema.org LocalBusiness structured data
- Customer accounts (username/email + Google OAuth via django-allauth), saved businesses, recently viewed, reviews, reports and notifications
- Marketplace listings, service bookings, enquiries, promotions and ad campaigns
- Owner dashboard (listings, bookings, reviews, analytics) and admin reports
- SEO: sitemap.xml, canonical URLs, Open Graph / Twitter meta tags

## Getting started (development)

```bash
python -m venv mtaa
mtaa\Scripts\activate              # Windows (use `source mtaa/bin/activate` on Linux/macOS)
pip install -r requirements.txt
copy .env.example .env             # then edit values (add DJANGO_SECRET_KEY etc.)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://localhost:8000/ and http://localhost:8000/admin/.

By default the project uses SQLite and the console email backend, so it runs
out of the box. Copy `.env.example` to `.env` and set real values for
`DJANGO_SECRET_KEY`, Google OAuth keys, etc.

## Production deployment

1. Set environment variables (see `.env.example`):
   - `DJANGO_SECRET_KEY` (long random string)
   - `DJANGO_DEBUG=false`
   - `DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`
   - `DATABASE_URL=postgres://user:pass@host:5432/mtaabiz` (PostgreSQL recommended)
   - `REDIS_URL=redis://host:6379/0` (optional, for shared cache)
   - `EMAIL_BACKEND=smtp` + SMTP credentials for real emails
   - `SITE_BASE_URL=https://yourdomain.com` (used for sitemap/canonical links)
   - `SENTRY_DSN` (optional error monitoring)
2. Run:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   gunicorn MtaaBiz.wsgi:application
   ```
3. Put a reverse proxy (nginx / Caddy) in front with TLS.

## Tests

```bash
python manage.py test
```

CI (`.github/workflows/ci.yml`) runs checks, migration checks, and the full
test suite against PostgreSQL 16 on every push and pull request.
