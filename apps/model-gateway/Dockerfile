FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10004 onecat && useradd --uid 10004 --gid onecat --create-home onecat
COPY apps/model-gateway/requirements.txt requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 8 -r requirements.txt
COPY apps/model-gateway/app.py app.py
USER onecat
EXPOSE 8010
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8010"]
