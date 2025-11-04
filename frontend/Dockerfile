# =========================
# Next.js 14 (Node 20, Alpine) - Frontend
# =========================

# ---- Builder ----
  FROM node:20-alpine AS builder
  WORKDIR /app
  ENV NEXT_TELEMETRY_DISABLED=1
  # NODE_ENV را در builder تنظیم نکن تا devDependencies هم نصب شوند (برای build لازم است)
  RUN apk add --no-cache libc6-compat
  
  # اگر env عمومی لازم داری، همین‌جا پاس می‌گیرن (Dokploy -> Build Args)
  ARG NEXT_PUBLIC_API_URL
  ARG NEXT_PUBLIC_WS_URL
  ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
  ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
  
  # فقط فایل‌های نصب را کپی کن تا cache بهتر عمل کند
  COPY package.json package-lock.json ./
  
  # اگر lock وجود داشت از ci استفاده کن، وگرنه نصب معمولی
  # (در Dokploy چون الان lock داخل frontend داری، ci اجرا می‌شود)
  RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
  
  # بقیه سورس
  COPY . .
  
  # اطمینان از وجود public (بی‌ضرر)
  RUN mkdir -p /app/public
  
  # بیلد
  RUN npm run build
  
  # ---- Runtime (standalone) ----
  FROM node:20-alpine AS production
  WORKDIR /app
  ENV NODE_ENV=production \
      PORT=3000 \
      HOSTNAME=0.0.0.0 \
      NEXT_TELEMETRY_DISABLED=1
  RUN apk add --no-cache libc6-compat curl
  
  # یوزر نان‌روت
  RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
  
  # خروجی standalone
  COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
  COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
  # اگر فایل/عکس عمومی داری:
  COPY --from=builder --chown=nextjs:nodejs /app/public ./public
  # کپی فایل‌های config برای PostCSS و Tailwind (در standalone mode لازم است)
  COPY --from=builder --chown=nextjs:nodejs /app/postcss.config.js ./postcss.config.js
  COPY --from=builder --chown=nextjs:nodejs /app/tailwind.config.js ./tailwind.config.js
  COPY --from=builder --chown=nextjs:nodejs /app/next.config.js ./next.config.js
  
  USER nextjs
  EXPOSE 3000
  
  # Healthcheck: اگر /api/health نداری، همون روت '/'
  HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1
  
  # Entry
  CMD ["node", "server.js"]
  