FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin app \
    && mkdir /data \
    && chown app:app /data

USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "65524", "--workers", "1", "--no-access-log"]
