# 📋 راهنمای تنظیم Environment Variables

## 🔧 تنظیمات مورد نیاز برای Frontend

### 1. ایجاد فایل `.env.local`

در مسیر `frontend/` یک فایل با نام `.env.local` ایجاد کنید:

```bash
cd frontend
cp .env.example .env.local
```

### 2. تنظیم متغیرهای محیطی

فایل `.env.local` را باز کنید و مقادیر زیر را تنظیم کنید:

```env
# آدرس Backend API
NEXT_PUBLIC_API_URL=http://localhost:8000

# آدرس WebSocket (اختیاری - فقط برای قابلیت‌های صوتی real-time)
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### 3. مقادیر برای محیط‌های مختلف

#### Development (محلی):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

#### Production:
```env
NEXT_PUBLIC_API_URL=https://api.aidepartment.net
NEXT_PUBLIC_WS_URL=wss://api.aidepartment.net/ws
```

### 4. نکات مهم

- ✅ فایل `.env.local` در `.gitignore` است و commit نمی‌شود
- ✅ بعد از تغییر `.env.local`، dev server را restart کنید
- ✅ برای production، این متغیرها باید در build time تنظیم شوند
- ⚠️ اگر `NEXT_PUBLIC_WS_URL` را خالی بگذارید، WebSocket غیرفعال می‌شود (بدون خطا)

### 5. بررسی تنظیمات

برای اطمینان از اینکه متغیرها درست تنظیم شده‌اند:

```javascript
// در browser console
console.log('API URL:', process.env.NEXT_PUBLIC_API_URL);
console.log('WS URL:', process.env.NEXT_PUBLIC_WS_URL);
```

## 🐛 حل مشکلات رایج

### مشکل: خطای "NEXT_PUBLIC_API_URL is not set"

**راه حل:**
1. مطمئن شوید فایل `.env.local` در مسیر `frontend/` وجود دارد
2. متغیر `NEXT_PUBLIC_API_URL` را اضافه کنید
3. Dev server را restart کنید

### مشکل: WebSocket errors در console

**راه حل:**
- این خطاها طبیعی هستند اگر WebSocket server در دسترس نباشد
- اگر نمی‌خواهید از WebSocket استفاده کنید، `NEXT_PUBLIC_WS_URL` را خالی بگذارید
- در production، خطاها به صورت خودکار suppress می‌شوند

### مشکل: API calls fail با 404

**راه حل:**
1. مطمئن شوید backend server در حال اجرا است
2. آدرس `NEXT_PUBLIC_API_URL` را بررسی کنید
3. در browser، Network tab را چک کنید که requests به آدرس درست می‌روند

## 📝 چک‌لیست

- [ ] فایل `.env.local` ایجاد شده
- [ ] `NEXT_PUBLIC_API_URL` تنظیم شده
- [ ] `NEXT_PUBLIC_WS_URL` تنظیم شده (یا خالی برای غیرفعال کردن)
- [ ] Dev server restart شده
- [ ] Backend server در حال اجرا است
- [ ] خطاها در console بررسی شده‌اند

