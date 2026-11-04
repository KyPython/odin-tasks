FROM node:22-alpine AS builder
RUN corepack enable && adduser -D appuser
WORKDIR /workspace
COPY . .
RUN chown -R appuser:appuser /workspace
USER appuser
RUN pnpm install --frozen-lockfile
RUN pnpm turbo run build --filter=@harbor/dispatch-api
