FROM python:3.11-slim

WORKDIR /app

# Copy and install requirements
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:app", "--workers", "2", "--threads", "4"]
