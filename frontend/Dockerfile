# =========================
# Frontend (Next.js 14) – Multi-stage, Prod & Dev targets
# =========================

# ---------- Base (مشترک) ----------
FROM node:20-alpine AS base
WORKDIR /app

# پیش‌نیازهای رایج next/image (sharp) روی Alpine
RUN apk add --no-cache libc6-compat

# یوزر نان‌روت
RUN addgroup -g 1001 -S nodejs \
 && adduser -S nextjs -u 1001

ENV NEXT_TELEMETRY_DISABLED=1

# ---------- Build Stage (نصب کامل → بیلد) ----------
FROM base AS builder

# بیلد باید production باشه تا هشدار Next نگیری
ENV NODE_ENV=production

# متغیرهای پابلیک که در زمان بیلد لازم‌اند
# (در Dokploy به صورت build args پاس بده)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}

# نصب کامل همه پکیج‌ها (dependencies + devDependencies برای بیلد)
COPY package*.json ./
RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps

# کپی کد پروژه
COPY . .

# بیلد Next.js (standalone output)
RUN npm run build

# پاکسازی کش npm برای کاهش حجم
RUN npm cache clean --force

# ---------- Runtime Stage (فقط standalone) ----------
FROM node:20-alpine AS production
WORKDIR /app

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1

# ابزار healthcheck
RUN apk add --no-cache curl

# فقط Artefact های لازم برای اجرای standalone
# .next/standalone شامل server.js و node_modules مینیمال است
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

# Healthcheck: ساده و قابل‌اعتماد
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -fsS http://127.0.0.1:3000/ || exit 1

# اجرای سرور Next.js با node server.js (standalone)
CMD ["node", "server.js"]

# ---------- Dev Target (اختیاری برای لوکال) ----------
# اگر خواستی در Docker با hot-reload توسعه بدی:
# docker build --target dev -t app-dev .
# و بعد با volume کد رو mount کن
FROM base AS dev
ENV NODE_ENV=development
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]