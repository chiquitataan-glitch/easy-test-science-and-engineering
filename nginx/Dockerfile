FROM node:20-slim AS frontend-builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx/nginx.ssl.conf /etc/nginx/nginx.conf

COPY --from=frontend-builder /app/dist /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
