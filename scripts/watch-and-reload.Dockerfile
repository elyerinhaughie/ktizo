FROM alpine:latest

# Install inotify-tools and docker CLI
RUN apk add --no-cache inotify-tools docker-cli bash

WORKDIR /app

COPY watch-dnsmasq.sh /app/watch-dnsmasq.sh
RUN chmod +x /app/watch-dnsmasq.sh

CMD ["/app/watch-dnsmasq.sh"]
