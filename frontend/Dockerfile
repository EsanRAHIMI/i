# =========================
# Next.js 14 – Multi-stage
# =========================

# ---- Dependencies (prod deps) ----
    FROM node:20-alpine AS dependencies
    WORKDIR /app
    ENV NEXT_TELEMETRY_DISABLED=1
    RUN apk add --no-cache libc6-compat
    COPY package*.json ./
    RUN npm ci --only=production && npm cache clean --force
    
    # ---- Builder (dev + build) ----
    FROM node:20-alpine AS builder
    WORKDIR /app
    ENV NEXT_TELEMETRY_DISABLED=1
    RUN apk add --no-cache libc6-compat
    # اگر envهای پابلیک لازم داری:
    ARG NEXT_PUBLIC_API_URL
    ARG NEXT_PUBLIC_WS_URL
    ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
    
    COPY package*.json ./
    # devDependencies هم لازمند برای build
    RUN npm ci
    COPY . .
    # اگر احتمالاً public نداری، این خط خالی‌اش می‌سازه (بی‌ضرر):
    RUN mkdir -p /app/public
    RUN npm run build
    
    # ---- Runtime (standalone) ----
    FROM node:20-alpine AS production
    WORKDIR /app
    ENV NODE_ENV=production \
        PORT=3000 \
        NEXT_TELEMETRY_DISABLED=1
    RUN apk add --no-cache libc6-compat curl
    # یوزر نان‌روت
    RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
    
    # کپی خروجی standalone
    COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
    COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
    # اگر واقعاً public داری و لازمته، این خط رو نگه دار؛ وگرنه حذفش کن:
    # COPY --from=builder --chown=nextjs:nodejs /app/public ./public
    
    USER nextjs
    EXPOSE 3000
    
    # Healthcheck: اگر /api/health نداری، روت رو بزن
    HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
      CMD curl -f http://localhost:3000/ || exit 1
    
    # Next.js standalone entrypoint
    CMD ["node", "server.js"]
    