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

Cloudinary upload flow:
- Set `CLOUDINARY_URL` plus `CLOUDINARY_UNSIGNED_EVIDENCE_PRESET` for direct browser uploads.
- The payment proof form uploads screenshots/PDFs directly to Cloudinary first, then stores only the Cloudinary metadata in the database.
- Admin creator/content uploads also use direct Cloudinary uploads, which avoids pushing large files through Render.
- For locked content, assets are uploaded as Cloudinary-authenticated media and rendered through signed delivery URLs.

How to create the unsigned preset:
1. Open the Cloudinary Console and go to `Settings` -> `Upload`.
2. In `Upload presets`, click `Add upload preset`.
3. Give it a name such as `ppv_evidence_unsigned` and mark it as `Unsigned`.
4. Restrict `allowed formats` to the file types you want, such as `jpg`, `png`, `webp`, `pdf`.
5. Set the folder to `ppv/evidence`.
6. Turn on `Disallow public ID` so browser uploads cannot choose their own IDs.
7. Keep `Generated public ID` on `Auto-generate an unguessable public ID value`.
8. For `Generated display name`, `Use the filename of the uploaded file as the asset's display name` is fine.
9. Optionally set a file size limit and any incoming transformations you want.
10. Save the preset, then set `CLOUDINARY_UNSIGNED_EVIDENCE_PRESET=ppv_evidence_unsigned` in your environment.

Notes on the options in the screenshot:
- `Asset folder` controls where Cloudinary organizes the asset in the console.
- `Disallow public ID` is a good safety setting for unsigned uploads.
- `Generated public ID` should stay auto-generated for evidence uploads so users cannot guess or overwrite assets.
- `Display name` only affects how the asset is shown in Cloudinary, not the actual delivery security.
- For browser uploads, the preset should be `Unsigned`; for admin-side signed uploads, the app uses the signature endpoint instead.
