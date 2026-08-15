FROM node:22-alpine AS build
WORKDIR /app
COPY web/package*.json ./
RUN npm install
COPY web/ ./
ARG VITE_BASE_PATH=/
ARG VITE_API_BASE_URL=/api/v2
ENV VITE_BASE_PATH=$VITE_BASE_PATH
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=6 CMD wget -q -O /dev/null http://localhost/ || exit 1
