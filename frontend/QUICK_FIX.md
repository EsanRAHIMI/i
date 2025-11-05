# 🚀 راهنمای سریع رفع مشکلات Console

## ⚡ راه حل سریع (5 دقیقه)

### مرحله 1: ایجاد فایل `.env.local`

در ترمینال، به مسیر `frontend` بروید و فایل `.env.local` را ایجاد کنید:

```bash
cd frontend
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
EOF
```

یا به صورت دستی:
1. در مسیر `frontend/` یک فایل جدید با نام `.env.local` ایجاد کنید
2. محتوای زیر را در آن قرار دهید:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### مرحله 2: بررسی تنظیمات

```bash
cd frontend
npm run check-env
```

### مرحله 3: Restart کردن Dev Server

اگر dev server در حال اجرا است:
1. آن را متوقف کنید (Ctrl+C)
2. دوباره اجرا کنید: `npm run dev`

## ✅ تغییراتی که اعمال شد

### 1. **Logger مرکزی**
- تمام `console.log` ها به یک logger مرکزی تبدیل شدند
- در production، فقط خطاها log می‌شوند
- در development، همه چیز log می‌شود

### 2. **بهبود WebSocket**
- اگر WebSocket URL تنظیم نشده باشد، خطا نمی‌دهد
- تلاش‌های اتصال با exponential backoff انجام می‌شود
- بعد از 5 تلاش ناموفق، متوقف می‌شود

### 3. **Error Handling بهتر**
- خطاهای API به صورت graceful handle می‌شوند
- خطاهای غیرضروری suppress شده‌اند

## 🔍 بررسی مشکلات

### اگر هنوز خطا دارید:

1. **بررسی Environment Variables:**
   ```bash
   cd frontend
   npm run check-env
   ```

2. **بررسی Backend:**
   - مطمئن شوید backend server در حال اجرا است
   - آدرس `http://localhost:8000` را در مرورگر باز کنید
   - باید JSON response ببینید

3. **بررسی Console:**
   - مرورگر را refresh کنید
   - Console را باز کنید (F12)
   - فقط خطاهای واقعی باید نمایش داده شوند

## 📝 متغیرهای محیطی

### Development (محلی):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
```

### Production:
```env
NEXT_PUBLIC_API_URL=https://api.aidepartment.net
NEXT_PUBLIC_WS_URL=wss://api.aidepartment.net/ws
```

## ⚠️ نکات مهم

- ✅ فایل `.env.local` در `.gitignore` است (commit نمی‌شود)
- ✅ بعد از تغییر `.env.local`، dev server را restart کنید
- ✅ `NEXT_PUBLIC_WS_URL` اختیاری است - اگر خالی باشد، WebSocket غیرفعال می‌شود
- ✅ در production، خطاها به صورت خودکار suppress می‌شوند

## 🆘 اگر مشکل حل نشد

1. Console مرورگر را پاک کنید (Clear console)
2. Hard refresh کنید (Ctrl+Shift+R یا Cmd+Shift+R)
3. Dev server را restart کنید
4. Backend را بررسی کنید که در حال اجرا است

---

**برای اطلاعات بیشتر:** `ENV_SETUP_GUIDE.md` را بخوانید

