FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY agents ./agents
COPY core ./core
COPY switch ./switch
COPY adapters ./adapters
COPY data ./data
COPY prompts ./prompts
COPY room_templates ./room_templates
COPY alembic.ini ./
COPY alembic ./alembic

RUN pip install --no-cache-dir .

EXPOSE 8090

CMD ["uvicorn", "switch.server:app", "--host", "0.0.0.0", "--port", "8090"]
