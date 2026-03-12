# 🚀 راهنمای Deployment در Dokploy

## 📋 فایل‌های مورد نیاز برای Nixpacks

برای اینکه Nixpacks بتواند پروژه را بیلد و اجرا کند، نیاز به فایل‌های زیر دارید:

### 1. `Procfile` ✅ (ایجاد شد)
این فایل دستور start را مشخص می‌کند:
```
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### 2. `nixpacks.toml` ✅ (ایجاد شد)
این فایل پیکربندی دقیق‌تر Nixpacks را مشخص می‌کند.

### 3. `requirements.txt` ✅ (موجود است)
لیست وابستگی‌های Python.

## 🔧 تنظیمات Dokploy

### متغیرهای محیطی مورد نیاز:

در Dokploy → Environment Variables تنظیم کنید:

#### Database:
```
POSTGRES_HOST=postgres (یا آدرس دیتابیس)
POSTGRES_PORT=5432
POSTGRES_DB=i_assistant_prod
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
```

یا:
```
DATABASE_URL=postgresql://user:password@host:port/dbname
```

#### Redis:
```
REDIS_URL=redis://redis:6379/0
```

#### MinIO / S3:
```
MINIO_ENDPOINT=http://minio:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_BUCKET=app-bucket
```

#### Security:
```
JWT_SECRET=your_jwt_secret
ENCRYPTION_KEY=your_encryption_key
```

#### CORS & URLs:
```
BACKEND_CORS_ORIGINS=https://yourdomain.com
PUBLIC_BASE_URL=https://yourdomain.com
```

#### Optional - Voice Processing:
```
WHISPER_MODEL_SIZE=base
ELEVENLABS_API_KEY=your_key (optional)
```

#### Port (اختیاری):
```
PORT=8000
```

اگر Dokploy خودش PORT را تنظیم می‌کند، نیازی به تنظیم نیست.

## 📝 مراحل Deployment

### 1. Commit فایل‌های جدید:
```bash
git add backend/Procfile backend/nixpacks.toml
git commit -m "Add Nixpacks configuration for deployment"
git push
```

### 2. در Dokploy:
- رفتن به تنظیمات Application
- اطمینان از اینکه Build Pack روی "Nixpacks" تنظیم است
- تنظیم متغیرهای محیطی (Environment Variables)
- انجام Deploy

### 3. بررسی Logs:
اگر خطایی بود، در بخش Logs بررسی کنید:
```bash
# اگر دسترسی SSH دارید:
docker logs <container-name>
```

## 🐛 عیب‌یابی مشکلات رایج

### مشکل: "No start command could be found"
**حل شده**: فایل `Procfile` و `nixpacks.toml` ایجاد شده‌اند.

### مشکل: "Module not found"
**راه حل**: مطمئن شوید که:
- `requirements.txt` کامل است
- همه پکیج‌ها در requirements.txt هستند
- فایل `requirements.txt` در root دایرکتوری backend است

### مشکل: "Port already in use"
**راه حل**: در Dokploy، متغیر محیطی `PORT` را تنظیم کنید یا در `Procfile` از `$PORT` استفاده کنید.

### مشکل: "Database connection failed"
**راه حل**: 
- مطمئن شوید که متغیرهای محیطی دیتابیس درست تنظیم شده‌اند
- در صورت استفاده از Docker Compose، از نام سرویس به جای `localhost` استفاده کنید

## ✅ چک‌لیست Deployment

- [ ] `Procfile` در دایرکتوری backend وجود دارد
- [ ] `nixpacks.toml` در دایرکتوری backend وجود دارد
- [ ] `requirements.txt` به‌روز و کامل است
- [ ] تمام متغیرهای محیطی در Dokploy تنظیم شده‌اند
- [ ] فایل‌ها commit و push شده‌اند
- [ ] Health check endpoint کار می‌کند: `/health`

## 🔍 بررسی بعد از Deployment

```bash
# بررسی Health Check
curl https://your-domain.com/health

# بررسی API Documentation
curl https://your-domain.com/api/v1/docs
```

## 📚 منابع بیشتر

- [Nixpacks Documentation](https://nixpacks.com/docs)
- [Dokploy Documentation](https://dokploy.com/docs)




















