FROM python:3.12-alpine

# Install dependencies
RUN apk add --no-cache ffmpeg bash curl

# Install Python libs
RUN pip install --no-cache-dir yt-dlp flask gunicorn

# Storage folder
RUN mkdir -p /data

WORKDIR /app

COPY app.py /app/app.py
COPY templates /app/templates

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "300", "app:app"]
