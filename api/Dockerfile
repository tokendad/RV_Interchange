# Build context is the repo root (see docker-compose.yaml's `build.context`).
FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

COPY api /app/api

EXPOSE 8484

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8484"]
