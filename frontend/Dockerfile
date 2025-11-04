# ---------- Base ----------
  FROM node:20-alpine AS base
  WORKDIR /app
  RUN apk add --no-cache libc6-compat
  RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
  ENV NEXT_TELEMETRY_DISABLED=1
  
  # ---------- Builder ----------
  FROM base AS builder
  ENV NODE_ENV=production
  ARG NEXT_PUBLIC_API_URL
  ARG NEXT_PUBLIC_WS_URL
  ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
  ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
  COPY package*.json ./
  RUN npm ci --legacy-peer-deps || npm install --legacy-peer-deps
  COPY . .
  RUN npm run build
  RUN npm cache clean --force
  
  # ---------- Production ----------
  FROM node:20-alpine AS production
  WORKDIR /app
  ENV NODE_ENV=production \
      PORT=3000 \
      HOSTNAME=0.0.0.0 \
      NEXT_TELEMETRY_DISABLED=1
  RUN apk add --no-cache curl
  COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
  COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
  COPY --from=builder --chown=nextjs:nodejs /app/public ./public
  USER nextjs
  EXPOSE 3000
  HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://127.0.0.1:3000/ || exit 1
  CMD ["node", "server.js"]
  
  # ---------- Dev (اختیاری) ----------
  FROM base AS dev
  ENV NODE_ENV=development
  ENV NPM_CONFIG_PRODUCTION=false
  COPY package*.json ./
  RUN npm install --legacy-peer-deps
  COPY . .
  EXPOSE 3000
  CMD ["npm", "run", "dev"]
  