FROM python:3.12-alpine
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && addgroup -S syncer \
    && adduser -S -G syncer syncer
COPY sync.py .
USER syncer
CMD ["python", "-u", "sync.py"]
