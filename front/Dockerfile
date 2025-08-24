FROM node:22.18-alpine AS builder

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

RUN npm install -g pnpm

RUN pnpm install --frozen-lockfile

COPY . .

RUN pnpm build

FROM node:22.18-alpine AS production

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 8080

CMD [ "serve", "-s", "dist", "-l", "8080"]