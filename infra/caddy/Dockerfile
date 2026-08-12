FROM caddy:2.10.2-alpine@sha256:4c6e91c6ed0e2fa03efd5b44747b625fec79bc9cd06ac5235a779726618e530d

# The upstream binary carries a privileged-port file capability. Copying it
# removes that xattr so it can execute under no-new-privileges with all caps
# dropped while listening only on the unprivileged port 8080.
RUN cp /usr/bin/caddy /usr/bin/caddy-unprivileged \
    && chmod 0755 /usr/bin/caddy-unprivileged

USER 65532:65532

ENTRYPOINT ["/usr/bin/caddy-unprivileged"]
CMD ["run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
