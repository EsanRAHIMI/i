# =========================
# Next.js 14 – Dockerfile (npm, no lockfile)
# =========================

# ---- Builder ----
  FROM node:20-alpine AS builder
  WORKDIR /app
  ENV NEXT_TELEMETRY_DISABLED=1
  RUN apk add --no-cache libc6-compat
  
  # Build-time public envs (Dokploy -> Build Args)
  ARG NEXT_PUBLIC_API_URL
  ARG NEXT_PUBLIC_WS_URL
  ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
  ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
  
  # Install deps (dev deps needed for build)
  COPY package*.json ./
  RUN npm install --no-audit --no-fund
  
  # Copy source (must include postcss.config.js & tailwind.config.js)
  COPY . .
  RUN mkdir -p /app/public
  RUN npm run build
  
  # ---- Runtime (standalone) ----
  FROM node:20-alpine AS production
  WORKDIR /app
  ENV NODE_ENV=production \
      PORT=3000 \
      NEXT_TELEMETRY_DISABLED=1
  RUN apk add --no-cache libc6-compat curl
  
  # Non-root user
  RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
  
  # Copy runtime bits
  # 1) Standalone server + static assets
  COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
  COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
  # 2) Project files needed at runtime (fixes raw CSS resolution)
  COPY --from=builder --chown=nextjs:nodejs /app/next.config.js ./next.config.js
  COPY --from=builder --chown=nextjs:nodejs /app/app ./app
  # 3) Public assets if you use them
  # COPY --from=builder --chown=nextjs:nodejs /app/public ./public
  
  USER nextjs
  EXPOSE 3000
  
  HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -fsS http://localhost:3000/ || exit 1
  
  CMD ["node", "server.js"]
  