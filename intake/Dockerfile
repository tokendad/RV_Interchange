# Build context is the repository root (see deploy/docker-compose.yaml).
FROM python:3.12-slim

WORKDIR /app

COPY intake/requirements.txt /app/intake/requirements.txt
RUN pip install --no-cache-dir -r /app/intake/requirements.txt

COPY intake /app/intake

EXPOSE 8487

CMD ["uvicorn", "intake.app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8487"]
