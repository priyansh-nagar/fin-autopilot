FROM python:3.11-slim

WORKDIR /app/backend

COPY backend/ .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}
