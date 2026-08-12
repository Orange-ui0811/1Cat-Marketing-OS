FROM node:22-alpine@sha256:d2166de198f26e17e5a442f537754dd616ab069c47cc57b889310a717e0abbf9 AS build
WORKDIR /app
COPY apps/workspace/package*.json ./
RUN npm ci
COPY apps/workspace ./
RUN npm run build

FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
COPY infra/caddy/workspace-nginx-main.conf /etc/nginx/nginx.conf
COPY infra/caddy/workspace-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
