FROM python:3.12-slim

WORKDIR /app

COPY bot/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/config.py /app/backend/config.py
COPY backend/database.py /app/backend/database.py
COPY backend/models.py /app/backend/models.py
COPY backend/redis_client.py /app/backend/redis_client.py
COPY backend/__init__.py /app/backend/__init__.py
COPY bot/ /app/bot/

CMD ["python", "-m", "bot.main"]
