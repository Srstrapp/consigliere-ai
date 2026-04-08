# Frontend Dockerfile for Railway
FROM node:20-slim

WORKDIR /app

# Copy package files first for better caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source
COPY . .

# Build the Angular app
RUN npm run build

# Expose the SSR port (Angular Express server uses 4000 by default for SSR)
EXPOSE 3000

# Start the SSR server
CMD ["npm", "run", "serve:ssr:frontend"]
