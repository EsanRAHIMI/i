# راهنمای اجرای بک‌اند در لوکال

## مراحل اجرا

### 1. اطمینان از اجرای سرویس‌های Docker (دیتابیس‌ها)

ابتدا در پوشه‌ی اصلی پروژه (root) مطمئن شوید که سرویس‌های زیربنایی Docker در حال اجرا هستند:

```bash
docker-compose up -d
```

بررسی وضعیت:
```bash
docker ps
```

باید سرویس‌های زیر **Up** باشند:
- ✅ i-postgres
- ✅ i-redis
- ✅ i-minio

### 2. اجرای کل سیستم به صورت خودکار (پيشنهادی)

برای اجرای تمامی سرویس‌ها (Backend, Auth, Frontend) به صورت خودکار، کافی است در محیط مک اسکریپت زیر را از پوشه‌ی اصلی پروژه اجرا کنید:

```bash
./START.sh
```
این دستور به‌طور اتوماتیک تب‌های مجزا در Terminal باز کرده و سرویس‌ها را در محیط مجازی خودشان استارت می‌زند.

---

### 3. اجرای بک‌اند به صورت دستی

اگر قصد دارید فقط Backend را به صورت دستی مدیریت و اجرا کنید:

```bash
# ورود به دایرکتوری backend
cd backend

# ایجاد محیط مجازی با نام .venv (فقط بار اول)
python3 -m venv .venv

# فعال‌سازی محیط
source .venv/bin/activate

# نصب وابستگی‌ها
pip install --upgrade pip
pip install -r requirements.txt

# تنظیم مسیر پایتون
export PYTHONPATH=.:$PYTHONPATH

# اجرای سرور
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*(تمامی متغیرهای محیطی مستقیماً از فایل `backend/.env` خوانده خواهند شد)*

### 4. مدیریت دیتابیس (Migrations)

برای اعمال آپدیت‌ها و جدول‌های جدید، مایگریشن‌ها دیگر به صورت مستقل در بک‌اند اجرا نمی‌شوند. اکنون از سرویس مجزای `database/` استفاده می‌شود که هر دو سرویس `backend` و `auth` را به شکل یکپارچه مدیریت می‌کند.

اجرای مایگریشن روی آخرین تغییرات:
```bash
# از پوشه اصلی پروژه دستور زیر را استفاده کنید:
docker build -f database/Dockerfile -t database-migration .
docker run --rm --network app_app-network -e POSTGRES_DB=i_DB -e POSTGRES_USER=esan -e POSTGRES_PASSWORD=Admin_1234_1234 -e POSTGRES_HOST=i-postgres database-migration
```

### 5. بررسی سلامت بک‌اند

پس از اجرای بک‌اند:

```bash
# بررسی health endpoint
curl http://localhost:8000/health

# باید خروجی زیر را ببینید:
# {"status":"healthy","timestamp":1234567890.123,"version":"1.0.0"}
```

## آدرس‌های مهم

- **بک‌اند مستقیم**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/api/v1/docs

## عیب‌یابی

### اگر پورت 8000 در حال استفاده است:

```bash
# پیدا کردن پروسس استفاده‌کننده
lsof -i :8000

# متوقف کردن آن
kill -9 <PID>
```

### اگر بک‌اند شروع نمی‌شود:

1. بررسی اتصال به دیتابیسها در داکر:
   ```bash
   docker ps | grep postgres
   ```

2. بررسی کامل بودن مقادیر در `.env`:
   مطمئن شوید فایل `backend/.env` در جای خود قرار دارد و مقادیر درستی (همراه با اکانت لوکال پایگاه داده) در آن سِت شده است.
