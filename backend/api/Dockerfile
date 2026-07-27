FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN useradd --create-home --uid 10001 cakecity
COPY backend/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/api/app ./app
COPY backend/api/migrate.py ./migrate.py
COPY backend/api/start_free.py ./start_free.py
COPY database/migrations ./migrations
USER cakecity
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
