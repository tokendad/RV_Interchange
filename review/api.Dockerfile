FROM python:3.12-slim
WORKDIR /app
COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt 'PyJWT[crypto]==2.10.1'
COPY api /app/api
COPY intake /app/intake
COPY review /app/review
EXPOSE 8488
CMD ["uvicorn", "review.app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8488"]
