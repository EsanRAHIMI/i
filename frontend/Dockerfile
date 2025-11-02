# =========================
# Frontend (Next.js 14) – Multi-stage
# =========================

# 1) Dependencies layer (for caching npm)
FROM node:20-alpine AS deps
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
COPY package*.json ./
RUN npm install --legacy-peer-deps --ignore-scripts && npm cache clean --force

# 2) Builder layer
FROM node:20-alpine AS builder
WORKDIR /app
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# متغیرهای پابلیک برای بیلد (در Dokploy به صورت Build Args پاس بده)
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}

# نصب devDependencies با کش لایه قبلی
COPY package*.json ./
RUN npm install --legacy-peer-deps

# کد پروژه
COPY . .

# بیلد خروجی standalone
RUN npm run build

# 3) Runtime (production) – فقط خروجی لازم
FROM node:20-alpine AS production
WORKDIR /app

# یوزر غیر ریشه
RUN addgroup -g 1001 -S nodejs \
 && adduser -S nextjs -u 1001

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0 \
    NEXT_TELEMETRY_DISABLED=1

# کپی فقط Artefact های لازم برای اجرای standalone
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000

# Healthcheck با wget (در Alpine موجود است)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/ >/dev/null 2>&1 || exit 1

# اجرای سرور Next.js
CMD ["node", "server.js"]
