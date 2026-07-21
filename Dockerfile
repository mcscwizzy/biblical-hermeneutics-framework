FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BHF_MEMORY_PATH=/app/.bhf/sessions
ENV BHF_CKL_BACKEND=sqlite
ENV BHF_CKL_DATABASE_PATH=/app/.bhf/ckl.sqlite
ENV BHF_CKL_STALE_DATABASE_POLICY=error
# The lexical database is generated from developer-supplied source files and
# mounted at runtime. Raw lexical XML is deliberately not copied into the image.
ENV BHF_LEXICAL_DATABASE_PATH=/app/.bhf-data/lexicon.sqlite

WORKDIR /app

RUN groupadd --gid 1000 bhf \
    && useradd --uid 1000 --gid bhf --home-dir /app --shell /usr/sbin/nologin bhf

COPY tools/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy the repository content after dependency install so image builds pick up
# new runtime assets, profiles, docs, and frontend source files together.
COPY . .

RUN mkdir -p /app/.bhf/sessions /app/.bhf/exports /app/.bhf-data/sessions \
    && python -m framework.canonical_library build-db --output /app/.bhf/ckl.sqlite \
    && python -m framework.canonical_library verify-db --database /app/.bhf/ckl.sqlite --skip-fingerprint \
    && chown -R bhf:bhf /app

USER bhf

EXPOSE 8080

CMD ["uvicorn", "bhf_web.app:app", "--host", "0.0.0.0", "--port", "8080"]
