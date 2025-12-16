FROM python:3.11-slim

WORKDIR /app

COPY services/cache-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/cache-service/app/ ./app/
COPY shared/ ./shared/

EXPOSE 8008

CMD ["python", "app/main.py"]