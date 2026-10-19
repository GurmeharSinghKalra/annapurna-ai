FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY data/crop_training_sample.csv ./data/crop_training_sample.csv
COPY scripts ./scripts

# The crop model is optional: the ranking falls back to transparent rules when it is absent, so a
# training failure must not fail the image build.
RUN python scripts/train_model.py || echo "crop model not trained; the API will use rules only"

# Run as a non-root user, and give it ownership of the writable data directory.
RUN useradd --create-home --uid 10001 annapurna \
    && mkdir -p /app/data /app/models \
    && chown -R annapurna:annapurna /app
USER annapurna

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).status==200 else 1)"

# Apply migrations, then serve. Running them here keeps a single-container deployment correct;
# a multi-replica deployment should run `alembic upgrade head` as a separate job instead.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
