FROM python:3.11-slim

WORKDIR /app

COPY services/embedding-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/embedding-service/app/ ./app/
COPY shared/ ./shared/

EXPOSE 8003

CMD ["python", "app/main.py"]