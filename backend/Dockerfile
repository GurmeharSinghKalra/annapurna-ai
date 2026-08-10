FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime dependencies only. Test tooling is in requirements-dev.txt and is not
# shipped to production.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data/crop_training_sample.csv ./data/crop_training_sample.csv
COPY scripts ./scripts

RUN python scripts/train_model.py

# The runtime writes the SQLite database into /app/data, so that path must be
# writable by the unprivileged user the container runs as.
RUN useradd --create-home --uid 10001 annapurna \
    && chown -R annapurna:annapurna /app
USER annapurna

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
