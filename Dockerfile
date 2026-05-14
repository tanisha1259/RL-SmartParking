FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY app.py ./app.py
COPY configs ./configs
COPY models ./models
COPY rl ./rl
COPY sim ./sim

EXPOSE 5001

CMD ["python", "app.py"]
