FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY configs /app/configs
COPY models /app/models
COPY rl /app/rl
COPY sim /app/sim

EXPOSE 5001

CMD ["python", "-m", "flask", "--app", "backend.app:create_app", "run", "--host=0.0.0.0", "--port=5001"]
