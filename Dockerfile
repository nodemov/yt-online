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

# Optimized for 2 CPU, 4GB RAM VPS
# Workers: (2 * CPU) + 1 = 5, but use 3-4 to leave resources for yt-dlp
# Threads: 2 per worker for better concurrency
# Worker class: gthread for streaming support
# Max requests: restart workers after 1000 requests to prevent memory leaks
CMD ["gunicorn", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "3", \
    "--threads", "2", \
    "--worker-class", "gthread", \
    "--timeout", "600", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "100", \
    "--worker-tmp-dir", "/dev/shm", \
    "app:app"]
