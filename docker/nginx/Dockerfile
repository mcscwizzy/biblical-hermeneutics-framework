FROM nginx:1.27-alpine

RUN mkdir -p /etc/nginx/certs

COPY docker/nginx/local-https.conf /etc/nginx/conf.d/default.conf
COPY .bhf/certs/localhost.crt /etc/nginx/certs/localhost.crt
COPY .bhf/certs/localhost.key /etc/nginx/certs/localhost.key

RUN chmod 644 /etc/nginx/certs/localhost.crt \
    && chmod 600 /etc/nginx/certs/localhost.key
