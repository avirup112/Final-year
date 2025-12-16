FROM python:3.11-slim

WORKDIR /app

COPY services/self-healing-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/self-healing-service/app/ ./app/
COPY shared/ ./shared/

EXPOSE 8007

CMD ["python", "app/main.py"]