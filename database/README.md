## Database service (migrations only)

این سرویس فقط برای اجرای migration ها ساخته شده تا بک‌اند و Auth جداگانه روی دیتابیس، به‌صورت مستقل ولی متمرکز مدیریت شوند.

### چرا لازم است؟
- `backend/` و `auth/` هر دو جدول‌های هم‌نام دارند (`users`, `user_settings`, `password_reset_tokens`).
- اگر هر دو روی یک schema مشترک migration بزنند، جدول‌ها روی هم می‌افتند و دیتابیس خراب می‌شود.

### استراتژی پیشنهادی (تفکیک‌شده و استاندارد)
- **Schema جدا برای هر سرویس**
  - `backend` → schema: `backend`
  - `auth` → schema: `auth`
- **Version table جدا**
  - backend: `backend_alembic_version`
  - auth: `auth_alembic_version` (هم‌اکنون در `auth/alembic/env.py` استفاده شده)

### اجرا
- این سرویس هنگام اجرا، migration های backend و auth را پشت سر هم اجرا می‌کند و سپس خارج می‌شود.
- ورودی‌ها از ENV:
  - `DATABASE_URL` یا متغیرهای `POSTGRES_*`
  - `DB_BACKEND_SCHEMA` (پیش‌فرض: `backend`)
  - `DB_AUTH_SCHEMA` (پیش‌فرض: `auth`)

### تست دستی
- backend migrations:
  - `alembic -c /database/alembic.backend.ini upgrade head`
- auth migrations:
  - `alembic -c /database/alembic.auth.ini upgrade head`

