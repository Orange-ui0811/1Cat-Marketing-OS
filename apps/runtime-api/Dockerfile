ARG DOCKER_HUB_REGISTRY=docker.io
FROM ${DOCKER_HUB_REGISTRY}/library/python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10001 onecat && useradd --uid 10001 --gid onecat --create-home onecat
COPY apps/runtime-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 8 -r /app/requirements.txt
COPY apps/runtime-api /app
COPY packages/contracts /contracts
RUN chown -R onecat:onecat /app
USER onecat
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
