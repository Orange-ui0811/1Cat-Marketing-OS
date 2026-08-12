FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN groupadd --gid 10003 onecat && useradd --uid 10003 --gid onecat --create-home onecat
COPY apps/organization-mcp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --timeout 120 --retries 8 -r requirements.txt
COPY apps/organization-mcp /app
RUN chown -R onecat:onecat /app
USER onecat
EXPOSE 8001
CMD ["python", "server.py"]
