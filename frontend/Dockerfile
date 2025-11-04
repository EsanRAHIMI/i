# =========================
# Next.js 14 – Dockerfile (npm, no lockfile)
# =========================

# ---- Builder ----
  FROM node:20-alpine AS builder
  WORKDIR /app
  ENV NEXT_TELEMETRY_DISABLED=1
  
  # sharp deps for next/image
  RUN apk add --no-cache libc6-compat
  
  # Public envs for build-time (Optional: Dokploy -> Build Args)
  ARG NEXT_PUBLIC_API_URL
  ARG NEXT_PUBLIC_WS_URL
  ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
  ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
  
  # Install dev deps for build (no package-lock.json → use npm install)
  COPY package*.json ./
  RUN npm install --no-audit --no-fund
  
  # Copy source and build
  COPY . .
  # If repo may miss public/, keep it harmless:
  RUN mkdir -p /app/public
  RUN npm run build
  
  # ---- Runtime (standalone) ----
  FROM node:20-alpine AS production
  WORKDIR /app
  ENV NODE_ENV=production \
      PORT=3000 \
      NEXT_TELEMETRY_DISABLED=1
  
  # runtime needs
  RUN apk add --no-cache libc6-compat curl
  
  # non-root user
  RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
  
  # Copy standalone output only
  COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
  COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
  # If you actually use /public at runtime, uncomment the next line and ensure it exists in repo:
  # COPY --from=builder --chown=nextjs:nodejs /app/public ./public
  
  USER nextjs
  EXPOSE 3000
  
  # If you don't have /api/health, keep root path:
  HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -fsS http://localhost:3000/ || exit 1
  
  # Next.js standalone entrypoint (requires next.config.js -> output: 'standalone')
  CMD ["node", "server.js"]
  