# 🚀 راهنمای سریع برای توسعه Frontend با Hot Reload

## ⚡ روش 1: اجرای Local (سریع‌ترین - توصیه می‌شود)

این روش **سریع‌ترین** است و برای توسعه عالی کار می‌کند:

```bash
# فقط frontend را به صورت local اجرا کنید
./scripts/dev-frontend-local.sh
```

یا به صورت دستی:

```bash
cd frontend
npm install  # فقط یک بار
npm run dev
```

**مزایا:**
- ✅ سریع‌ترین hot reload
- ✅ نیازی به Docker نیست
- ✅ تغییرات فوری در مرورگر قابل مشاهده است
- ✅ مناسب برای توسعه UI و کامپوننت‌ها

**دسترسی:**
- Frontend: http://localhost:3000

---

## 🐳 روش 2: اجرای با Docker Dev Mode

اگر می‌خواهید همه سرویس‌ها (backend, database, etc.) را هم داشته باشید:

### شروع همه سرویس‌ها:

```bash
# استفاده از docker-compose.dev.yml (نه docker-compose.yml!)
docker-compose -f docker-compose.dev.yml up -d
```

### فقط Frontend + سرویس‌های پایه:

```bash
docker-compose -f docker-compose.dev.yml up -d frontend postgres redis minio
```

### مشاهده لاگ‌های Frontend:

```bash
docker-compose -f docker-compose.dev.yml logs -f frontend
```

**مزایا:**
- ✅ Hot reload خودکار
- ✅ همه سرویس‌ها در دسترس هستند
- ✅ شبیه‌سازی محیط production

**دسترسی:**
- Frontend: http://localhost:3000
- با Nginx: http://localhost (اگر با profile اجرا کنید)

---

## ⚠️ مشکل رایج: استفاده از docker-compose.yml به جای docker-compose.dev.yml

**❌ اشتباه:**
```bash
docker-compose up  # این production mode است!
```

**✅ درست:**
```bash
docker-compose -f docker-compose.dev.yml up  # این development mode است!
```

---

## 🔄 Restart Frontend برای اعمال تغییرات

### در حالت Local:
- فقط فایل را ذخیره کنید - تغییرات خودکار اعمال می‌شود!

### در حالت Docker:
```bash
# Restart فقط frontend
docker-compose -f docker-compose.dev.yml restart frontend

# یا rebuild (اگر package.json تغییر کرد)
docker-compose -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.dev.yml up -d frontend
```

---

## 🛑 توقف سرویس‌ها

### Local:
```bash
# Ctrl+C در ترمینال
```

### Docker:
```bash
# توقف همه
docker-compose -f docker-compose.dev.yml down

# فقط frontend
docker-compose -f docker-compose.dev.yml stop frontend
```

---

## 📝 نکات مهم

1. **همیشه برای توسعه از `docker-compose.dev.yml` استفاده کنید**
   - `docker-compose.yml` برای production است و hot reload ندارد

2. **برای تغییرات کد، نیازی به rebuild نیست**
   - فقط فایل را ذخیره کنید
   - Next.js خودکار تغییرات را detect می‌کند

3. **برای تغییرات در `package.json`:**
   ```bash
   # Local
   npm install
   
   # Docker
   docker-compose -f docker-compose.dev.yml build frontend
   ```

4. **اگر hot reload کار نمی‌کند:**
   - مطمئن شوید `NODE_ENV=development` است
   - Volume mount شده باشد (در Docker)
   - Port 3000 آزاد باشد

---

## 🐛 عیب‌یابی

### Port 3000 اشغال است:
```bash
# پیدا کردن process
lsof -ti:3000

# یا تغییر پورت در package.json
# "dev": "next dev -p 3001"
```

### تغییرات اعمال نمی‌شود:
```bash
# Clear cache
cd frontend
rm -rf .next
npm run dev
```

### در Docker hot reload کار نمی‌کند:
```bash
# بررسی volume mount
docker-compose -f docker-compose.dev.yml config | grep volumes

# Rebuild
docker-compose -f docker-compose.dev.yml build --no-cache frontend
docker-compose -f docker-compose.dev.yml up -d frontend
```





