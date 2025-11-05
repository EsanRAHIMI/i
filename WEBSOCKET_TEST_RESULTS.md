# گزارش تست WebSocket

## وضعیت تست

### ✅ Backend در حال اجرا است
- Process ID: 94445
- Port: 8000
- Health check: ✅ پاسخ می‌دهد

### ⚠️ نیاز به Restart

**مشکل:** Backend در حال اجرا است اما تغییرات جدید هنوز اعمال نشده‌اند.

**علت:** 
- تست با curl یک `500 Internal Server Error` داد
- لاگ‌های WebSocket در لاگ‌ها مشاهده نشد
- احتمالاً backend قبل از اعمال تغییرات راه‌اندازی شده

### 🔧 راه حل

**Backend را restart کنید:**

```bash
# اگر با uvicorn مستقیم اجرا می‌کنید:
# Ctrl+C در ترمینال backend
# سپس دوباره اجرا کنید:
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# یا اگر با script اجرا می‌کنید:
./scripts/run-backend-local.sh
```

### 📋 تست‌های انجام شده

1. ✅ **Health Check**: Backend پاسخ می‌دهد
2. ❌ **WebSocket Handshake**: 500 Error (نیاز به restart)
3. ⏳ **Logs**: لاگ‌های WebSocket مشاهده نشد (نیاز به restart)

### 🔍 بعد از Restart، تست‌های زیر را انجام دهید:

#### 1. تست با wscat:
```bash
wscat -c "ws://localhost:8000/ws?session_id=test123"
```

#### 2. تست با مرورگر:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws?session_id=browser_test');
ws.onopen = () => console.log('✅ Connected');
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  console.log('📨', msg);
  if (msg.type === 'ping') {
    ws.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }));
  }
};
ws.onclose = (e) => console.log('❌ Closed', e.code, e.reason);
```

#### 3. بررسی لاگ‌ها:
```bash
tail -f backend/logs/backend.log | grep -i websocket
```

### 📝 انتظارات بعد از Restart

1. ✅ **Connection Log**: باید لاگ connection attempt را ببینید
2. ✅ **Authentication Log**: اگر token دارید، باید authentication log ببینید
3. ✅ **Heartbeat Log**: بعد از 30 ثانیه باید ping log ببینید
4. ✅ **Disconnection Log**: وقتی disconnect می‌کنید، باید log ببینید

### 🎯 نتیجه

**وضعیت فعلی:** ⚠️ نیاز به Restart Backend

**بعد از Restart:** باید همه چیز کار کند

**نکته:** اگر بعد از restart هنوز مشکل داشتید، لاگ‌ها را بررسی کنید و خطاهای دقیق را گزارش دهید.

