FROM nginxinc/nginx-unprivileged:1.29-alpine

# This image already runs as non-root (UID 101) and listens on 8080.
# We just drop in our config and content.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1

EXPOSE 8080
