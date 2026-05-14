FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY langGraph_agent ./langGraph_agent
COPY docker/start-backend.sh /usr/local/bin/start-backend

RUN chmod +x /usr/local/bin/start-backend \
    && mkdir -p \
      /app/langGraph_agent/smart_data_analysis_assistant/import_jobs \
      /app/langGraph_agent/smart_data_analysis_assistant/exports \
      /app/langGraph_agent/smart_data_analysis_assistant/audit_logs \
      /app/langGraph_agent/smart_data_analysis_assistant/chatbi_graph/output

EXPOSE 9008

CMD ["start-backend"]
