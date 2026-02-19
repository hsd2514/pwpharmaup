# PharmaGuard AI - Frontend Dockerfile
# Multi-stage build for production

# ============================================
# Stage 1: Build
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# Build-time API URL for Vite
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# ============================================
# Stage 2: Production
# ============================================
FROM nginx:alpine AS production

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
