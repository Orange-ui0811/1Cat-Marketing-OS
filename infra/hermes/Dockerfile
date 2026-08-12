FROM nousresearch/hermes-agent@sha256:a2d03767b0f9a619baeac47b278f1f5d9edbd7d2dff55eecbe3f99362988b971

USER root
WORKDIR /opt/hermes

# The upstream release image supplies the native/runtime dependency closure.
# Application source is always replaced by the project's immutable snapshot.
COPY --chown=root:root vendor/hermes-agent/ /opt/hermes/
RUN test "$(sed -n 's/^version = "\([^"]*\)"/\1/p' pyproject.toml | head -1)" = "0.20.0" && \
    test "$(cat UPSTREAM_COMMIT)" = "3c27eb6234bf91b8ceee9e9071591b31e9b148cb" && \
    printf '%s\n' '3c27eb6234bf91b8ceee9e9071591b31e9b148cb' > /opt/hermes/.hermes_build_sha

