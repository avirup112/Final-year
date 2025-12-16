FROM python:3.11-slim

WORKDIR /app

COPY services/ui-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ui-service/app/ ./app/
COPY shared/ ./shared/

EXPOSE 8501

# Streamlit configuration
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["streamlit", "run", "app/main.py"]