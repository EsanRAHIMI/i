# 🚀 راهنمای سریع Frontend Development

## برای اعمال تغییرات و مشاهده زنده در مرورگر:

### 1️⃣ راه‌اندازی اولیه (فقط یک بار):

```bash
docker-compose -f docker-compose.dev.yml up -d frontend postgres redis minio
```

### 2️⃣ برای هر تغییر در کد:

**هیچ کاری لازم نیست!** 🎉

- فقط کد را ویرایش کنید
- تغییرات به صورت خودکار در مرورگر اعمال می‌شود (Hot Reload)
- باز کردن: http://localhost:3000

### 3️⃣ فقط در موارد خاص نیاز به Rebuild:

```bash
# فقط زمانی که package.json تغییر کرده یا dependencies اضافه کردید:
docker-compose -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.dev.yml up -d frontend
```

### 4️⃣ دستورات مفید:

```bash
# مشاهده لاگ‌های زنده
docker-compose -f docker-compose.dev.yml logs -f frontend

# متوقف کردن
docker-compose -f docker-compose.dev.yml down

# مشاهده وضعیت
docker-compose -f docker-compose.dev.yml ps
```

---

## 📝 خلاصه:

✅ **تغییرات کد**: هیچ کاری لازم نیست - Hot Reload خودکار  
✅ **تغییرات package.json**: فقط `build` و `up` دوباره  
✅ **دسترسی**: http://localhost:3000  

همه چیز آماده است! فقط کد را ویرایش کنید و نتیجه را ببینید. 🎯
