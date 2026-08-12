FROM alpine:3.22@sha256:14358309a308569c32bdc37e2e0e9694be33a9d99e68afb0f5ff33cc1f695dce

RUN apk add --no-cache tinyproxy ca-certificates

COPY infra/egress-proxy/tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY infra/egress-proxy/filter /etc/tinyproxy/filter

EXPOSE 3128

USER tinyproxy

CMD ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
