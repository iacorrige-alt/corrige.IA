# Stage 1: build da aplicação React
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_API_URL precisa estar disponível no build (injetada pelo Railway como build arg)
ARG VITE_API_URL

RUN npm run build

# Stage 2: servir com nginx
FROM nginx:alpine

# Copia o build gerado
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia a configuração como template (usa $PORT em runtime)
COPY nginx.conf /etc/nginx/conf.d/default.conf.template

EXPOSE 8080

CMD ["/bin/sh", "-c", "envsubst '$PORT' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
