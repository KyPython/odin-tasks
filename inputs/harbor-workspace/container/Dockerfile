FROM node:22-alpine AS builder
WORKDIR /workspace
COPY . .
RUN corepack enable && pnpm install --frozen-lockfile
RUN pnpm turbo run build --filter=@harbor/dispatch-api
