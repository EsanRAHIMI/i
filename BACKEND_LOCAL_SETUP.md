# راهنمای اجرای بک‌اند در لوکال

## مراحل اجرا

### 1. اطمینان از اجرای سرویس‌های Docker

ابتدا مطمئن شوید که سرویس‌های Docker در حال اجرا هستند:

```bash
docker-compose up -d
```

بررسی وضعیت:
```bash
docker ps
```

باید سرویس‌های زیر **healthy** باشند:
- ✅ i-postgres (healthy)
- ✅ i-redis (healthy)
- ✅ i-minio (healthy)

### 2. اجرای بک‌اند در لوکال

#### روش 1: استفاده از اسکریپت (پیشنهادی)

```bash
cd /Users/ehsanrahimi/Works/i/app
./scripts/run-backend-local.sh
```

#### روش 2: اجرای دستی

```bash
# ورود به دایرکتوری backend
cd backend

# ایجاد و فعال‌سازی محیط مجازی (فقط بار اول)
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
pip install --upgrade pip
pip install -r requirements.txt

# تنظیم متغیرهای محیطی
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=i_DB
export POSTGRES_USER=esan
export POSTGRES_PASSWORD=Admin_1234_1234
export REDIS_URL=redis://localhost:6379/0
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=esan
export MINIO_SECRET_KEY=Admin_1234_1234
export PYTHONPATH=$(pwd)
export TESTING=false

# اجرای migrations (اگر قبلاً انجام نشده)
alembic upgrade head

# اجرای سرور
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. بررسی سلامت بک‌اند

پس از اجرای بک‌اند، در یک ترمینال جدید:

```bash
# بررسی health endpoint
curl http://localhost:8000/health

# باید خروجی زیر را ببینید:
# {"status":"healthy","timestamp":1234567890.123,"version":"1.0.0"}
```

### 4. بررسی وضعیت Nginx

پس از اجرای بک‌اند، Nginx باید بتواند به آن متصل شود:

```bash
# بررسی health check nginx
curl http://localhost/health

# بررسی وضعیت کانتینرها
docker ps
```

بعد از چند ثانیه، `i-nginx` باید از `unhealthy` به `healthy` تغییر کند.

## آدرس‌های مهم

- **بک‌اند مستقیم**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/api/v1/docs
- **از طریق Nginx**: http://localhost/api/v1/docs

## عیب‌یابی

### اگر پورت 8000 در حال استفاده است:

```bash
# پیدا کردن پروسس استفاده‌کننده
lsof -i :8000

# متوقف کردن آن
kill -9 <PID>
```

### اگر بک‌اند شروع نمی‌شود:

1. بررسی لاگ‌ها:
   ```bash
   tail -f backend/logs/backend.log
   ```

2. بررسی اتصال به دیتابیس:
   ```bash
   docker ps | grep postgres
   ```

3. بررسی migration:
   ```bash
   cd backend
   source venv/bin/activate
   alembic current
   ```

### اگر Nginx هنوز unhealthy است:

1. بررسی لاگ nginx:
   ```bash
   docker logs i-nginx
   ```

2. بررسی اتصال nginx به backend:
   ```bash
   docker exec i-nginx wget -O- http://host.docker.internal:8000/health
   ```

## نکات مهم

- بک‌اند باید روی `0.0.0.0:8000` اجرا شود (نه فقط `localhost`) تا nginx بتواند به آن دسترسی داشته باشد
- از `--reload` استفاده کنید تا با هر تغییر در کد، سرور به‌صورت خودکار restart شود
- اگر خطایی رخ داد، لاگ‌ها را در `backend/logs/` بررسی کنید

