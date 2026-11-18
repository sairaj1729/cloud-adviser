# ==========================================
# Cloud Advisor Frontend - Multi-stage Build
# ==========================================

# -----------------
# 1. Builder Stage
# -----------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install build essentials if required by native dependencies
RUN apk add --no-cache libc6-compat

# Copy package descriptors first to leverage Docker layer caching
COPY package.json package-lock.json ./

# Install all dependencies cleanly
RUN npm ci

# Copy application source files
COPY . .

# Set build environment: build Node.js production server with SSR & static assets
ENV NITRO_PRESET=node-server
ARG VITE_API_URL=http://localhost:8000/api
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# -----------------
# 2. Production Stage
# -----------------
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8080
ENV HOST=0.0.0.0

# Copy built server bundle, public client assets, and package descriptors
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

# Expose HTTP port
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:8080/ || exit 1

# Start the optimized Node.js SSR server
CMD ["node", "dist/server/index.mjs"]
