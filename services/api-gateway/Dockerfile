FROM python:3.11-slim

WORKDIR /app

COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api-gateway/app/ ./app/
COPY shared/ ./shared/

EXPOSE 8080

CMD ["python", "app/main.py"]