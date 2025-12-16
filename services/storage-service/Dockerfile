FROM python:3.11-slim

WORKDIR /app

COPY services/storage-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/storage-service/app/ ./app/
COPY shared/ ./shared/

EXPOSE 8004

CMD ["python", "app/main.py"]