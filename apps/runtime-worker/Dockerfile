FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/runtime
WORKDIR /worker
RUN groupadd --gid 10002 onecat && useradd --uid 10002 --gid onecat --create-home onecat
COPY apps/runtime-worker/requirements.txt /worker/requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 8 -r /worker/requirements.txt
COPY apps/runtime-api /runtime
COPY apps/runtime-worker /worker
RUN chown -R onecat:onecat /worker /runtime
USER onecat
CMD ["python", "worker.py"]
