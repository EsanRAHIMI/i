# راهنمای توسعه Frontend با Hot Reload

## 🚀 راه‌حل‌های سریع برای توسعه

### روش 1: استفاده از Docker Compose Development (توصیه می‌شود)

این روش بهترین گزینه برای توسعه است چون:
- ✅ Hot Reload خودکار (تغییرات فوری در مرورگر)
- ✅ نیازی به rebuild با هر تغییر نیست
- ✅ فقط frontend rebuild می‌شود، بقیه سرویس‌ها دست نخورده می‌مانند

#### شروع Development Mode:

```bash
# شروع همه سرویس‌های مورد نیاز (postgres, redis, minio)
docker-compose -f docker-compose.dev.yml up -d

# یا فقط frontend + سرویس‌های پایه
docker-compose -f docker-compose.dev.yml up -d frontend postgres redis minio
```

#### مشاهده لاگ‌های Frontend:

```bash
docker-compose -f docker-compose.dev.yml logs -f frontend
```

#### دسترسی:
- Frontend: http://localhost:3000
- مستقیماً از پورت 3000 استفاده کنید (نیازی به nginx نیست)

---

### روش 2: استفاده از اسکریپت‌های آماده

#### شروع سریع:

```bash
./scripts/dev-frontend.sh
```

این اسکریپت:
- Frontend را در development mode راه‌اندازی می‌کند
- اگر قبلاً اجرا شده، فقط rebuild می‌کند

#### Rebuild فقط Frontend:

```bash
# برای development
./scripts/rebuild-frontend.sh dev

# برای production
./scripts/rebuild-frontend.sh prod
```

---

### روش 3: استفاده مستقیم از Docker Compose

#### Rebuild فقط Frontend (بدون تأثیر روی بقیه):

```bash
# Development mode
docker-compose -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.dev.yml up -d frontend

# Production mode (اگر نیاز به تست production build دارید)
docker-compose build frontend
docker-compose up -d frontend
```

---

## 🔄 تفاوت Development vs Production

### Development Mode (`docker-compose.dev.yml`):
- ✅ Hot Reload فعال
- ✅ Volume mount برای تغییرات فوری
- ✅ NODE_ENV=development
- ✅ Fast Refresh Next.js

### Production Mode (`docker-compose.yml`):
- ❌ نیاز به rebuild برای هر تغییر
- ❌ Optimized build
- ❌ NODE_ENV=production

---

## 📝 دستورات مفید

### مشاهده وضعیت سرویس‌ها:
```bash
docker-compose -f docker-compose.dev.yml ps
```

### متوقف کردن همه:
```bash
docker-compose -f docker-compose.dev.yml down
```

### متوقف کردن فقط Frontend:
```bash
docker-compose -f docker-compose.dev.yml stop frontend
```

### مشاهده لاگ‌های همه:
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

### اجرای دستور در Container:
```bash
docker-compose -f docker-compose.dev.yml exec frontend sh
```

---

## ⚡ نکات مهم برای عملکرد بهتر

1. **برای Development از `docker-compose.dev.yml` استفاده کنید**
   - Hot reload خودکار
   - نیازی به rebuild نیست

2. **فقط Frontend را Rebuild کنید**
   ```bash
   docker-compose -f docker-compose.dev.yml build frontend
   ```

3. **برای تغییرات Dependencies**
   - فقط باید rebuild کنید (بعد از تغییر package.json)
   - تغییرات کد نیازی به rebuild ندارد

4. **Volume Mounts**
   - کد شما در `./frontend` به container mount شده
   - تغییرات فوری اعمال می‌شوند

---

## 🐛 عیب‌یابی

### مشکل: Hot Reload کار نمی‌کند
```bash
# بررسی کنید که volume mount شده باشد
docker-compose -f docker-compose.dev.yml config | grep volumes -A 5

# Restart frontend
docker-compose -f docker-compose.dev.yml restart frontend
```

### مشکل: Port 3000 اشغال است
```bash
# بررسی process روی پورت 3000
lsof -ti:3000

# یا تغییر پورت در docker-compose.dev.yml
ports:
  - "3001:3000"  # استفاده از پورت 3001
```

### مشکل: node_modules مشکلات دارد
```bash
# Rebuild کامل
docker-compose -f docker-compose.dev.yml build --no-cache frontend
docker-compose -f docker-compose.dev.yml up -d frontend
```

---

## 📚 منابع بیشتر

- [Next.js Development Documentation](https://nextjs.org/docs/getting-started)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Volume Mounts](https://docs.docker.com/storage/volumes/)
