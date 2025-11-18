# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with clean slate
RUN npm ci --prefer-offline --no-audit --no-fund

# Copy source code
COPY . .

# Set environment for production build
ENV VITE_API_URL=""
ENV NODE_ENV=production

# Build application
RUN npm run build

# Production stage
FROM nginx:1.25-alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start nginx (runs as root in container, which is safe in Docker)
CMD ["nginx", "-g", "daemon off;"]