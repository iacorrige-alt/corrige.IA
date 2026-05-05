# Stage 1: build da aplicação React
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# As variáveis VITE_ precisam estar disponíveis no build
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_URL

RUN npm run build

# Stage 2: servir com nginx
FROM nginx:alpine

# Copia o build gerado
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia a configuração customizada do nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
