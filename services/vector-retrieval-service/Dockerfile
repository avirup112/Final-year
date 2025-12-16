FROM python:3.11-slim

WORKDIR /app

COPY services/vector-retrieval-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/vector-retrieval-service/app/ ./app/
COPY shared/ ./shared/

EXPOSE 8005

CMD ["python", "app/main.py"]