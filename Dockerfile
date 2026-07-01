FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BHF_MEMORY_PATH=/app/.bhf/sessions

WORKDIR /app

RUN groupadd --gid 1000 bhf \
    && useradd --uid 1000 --gid bhf --home-dir /app --shell /usr/sbin/nologin bhf

COPY tools/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY bhf_agent/ ./bhf_agent/
COPY bhf_web/ ./bhf_web/
COPY framework/ ./framework/
COPY profiles/ ./profiles/

RUN mkdir -p /app/.bhf/sessions /app/.bhf/exports \
    && chown -R bhf:bhf /app

USER bhf

EXPOSE 8080

CMD ["uvicorn", "bhf_web.app:app", "--host", "0.0.0.0", "--port", "8080"]
