# PPV Digital Content Unlock (Manual Verification)

Minimal Django app for selling pay-per-view digital media with **manual** payment verification in Django Admin. Customers get a **24-hour, link-based** access window (no login).

## Local setup

1. Install deps: `python -m pip install -r requirements.txt`
2. Run migrations: `python manage.py migrate`
3. Create admin user: `python manage.py createsuperuser`
4. Start server: `python manage.py runserver`

## Use

- Admin: `http://127.0.0.1:8000/admin/`
- Create `Payment settings` (bank/PayPal/crypto details)
- Create `Creator`, then `Content`
- Share a content URL: `/content/<content_uuid>/` (shown on Content admin list)
- Review `Payment requests` in admin and approve/reject

## Demo seed (optional)

- Seed demo settings + content (+ a pending request): `python manage.py seed_demo --with-request`

## Deploy (Render/VPS)

This repo includes a `render.yaml` Blueprint at `render.yaml:1`.

1. Create a new Blueprint in Render and point it at your repo (recommended)
2. Set your custom domain (optional) and update `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`
3. Ensure you have a persistent disk (needed for `media/` + `private_media/` uploads)

Render runs:
- Build: installs deps + `collectstatic`
- Pre-deploy: `migrate`
- Start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

Notes:
- Public previews use `MEDIA_ROOT` (`media/`), but paid content + evidence are stored under `PRIVATE_STORAGE_ROOT` (`private_media/`) via `django-private-storage`.
- In production, ensure your platform does **not** serve `private_media/` directly; content is only served through `/protected/<slug>/`.
- Render note: `render.yaml` mounts a disk at `/opt/render/project/src/storage` and sets `MEDIA_ROOT` + `PRIVATE_STORAGE_ROOT` there so uploads persist across deploys.
