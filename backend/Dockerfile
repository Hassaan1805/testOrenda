FROM python:3.11-slim

WORKDIR /app

# Backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code + frontend assets
COPY backend/ ./
COPY frontend/ ./frontend

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV ORENDA_DB_PATH=/data/orenda.sqlite3

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
