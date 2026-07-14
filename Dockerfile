FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY config ./config
COPY eval ./eval
COPY scripts ./scripts
COPY src ./src

RUN pip install --no-cache-dir .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
