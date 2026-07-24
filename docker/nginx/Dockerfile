FROM nginx:1.27-alpine AS certs

RUN mkdir -p /etc/nginx/certs
RUN apk add --no-cache openssl \
    && openssl req -x509 -nodes -newkey rsa:2048 -sha256 -days 825 \
        -keyout /etc/nginx/certs/localhost.key \
        -out /etc/nginx/certs/localhost.crt \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1" \
    && chmod 644 /etc/nginx/certs/localhost.crt \
    && chmod 600 /etc/nginx/certs/localhost.key

FROM nginx:1.27-alpine

COPY docker/nginx/local-https.conf /etc/nginx/conf.d/default.conf
COPY --from=certs /etc/nginx/certs/localhost.crt /etc/nginx/certs/localhost.crt
COPY --from=certs /etc/nginx/certs/localhost.key /etc/nginx/certs/localhost.key
