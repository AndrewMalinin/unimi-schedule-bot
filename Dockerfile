FROM python:3.13-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Fallback, если volume ./bot не смонтирован (в compose код берётся с хоста).
COPY bot/ bot/

CMD ["python", "-m", "bot"]
