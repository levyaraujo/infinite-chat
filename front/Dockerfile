FROM node:22.18-alpine AS builder

WORKDIR /app

# Accept API URL as build argument
ARG VITE_API_URL=/api

COPY package.json pnpm-lock.yaml ./

RUN npm install -g pnpm

RUN pnpm install --frozen-lockfile

COPY . .

# Set environment variable for Vite build
ENV VITE_API_URL=${VITE_API_URL}

RUN pnpm build

FROM node:22.18-alpine AS production

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 8080

CMD [ "serve", "-s", "dist", "-l", "8080"]