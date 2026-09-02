FROM python:3.12-slim

ARG BHF_HEBREW_LEXICON_REVISION=21c9add13bc727d3a951361778e97e3ff7afd1ce
ARG BHF_STRONGS_REVISION=0acd2f251c2d35ff8db2dece4e0593979d3ac223
ARG BHF_OSHB_REVISION=3d15126fb1ef74867fc1434be1942e837932691f
ARG BHF_MORPHGNT_REVISION=aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d
ARG BHF_TYNDALE_ARCHIVE_URL=https://tyndaleopenresources.com/wp-content/themes/tyndale-openresources/files/tyndale_open-studynotes.zip
ARG BHF_TYNDALE_ARCHIVE_SHA256=7b4d5ae088449d5a6925170c4b89b978acee2f78f73dc6b8a278fa948a7e8498

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BHF_MEMORY_PATH=/app/.bhf/sessions
ENV BHF_CKL_BACKEND=sqlite
ENV BHF_CKL_DATABASE_PATH=/app/.bhf/ckl.sqlite
ENV BHF_CKL_STALE_DATABASE_POLICY=error
ENV BHF_DATA_DIR=/app/.bhf-data
ENV BHF_COMMENTARY_SEED_POLICY=missing
# The Docker build generates seeded lexical and commentary databases. At
# runtime the entrypoint copies them into the mounted .bhf volume according to
# their respective seed policies and applies study-data migrations, including
# reviewed archaeology records and media.
ENV BHF_LEXICAL_DATABASE_PATH=/app/.bhf-data/lexicon.sqlite

WORKDIR /app

RUN groupadd --gid 1000 bhf \
    && useradd --uid 1000 --gid bhf --home-dir /app --shell /usr/sbin/nologin bhf

COPY . .
RUN pip install --no-cache-dir .

RUN chmod +x /app/scripts/docker-entrypoint.sh \
    && chmod +x /app/scripts/build-tyndale-database.sh \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && mkdir -p /tmp/bhf-lexical-sources /tmp/bhf-commentary /app/.bhf-seed \
    && /app/scripts/build-tyndale-database.sh \
        /tmp/bhf-commentary/tyndale_open-studynotes.zip \
        /app/.bhf-seed/commentary.sqlite \
        "$BHF_TYNDALE_ARCHIVE_URL" \
        "$BHF_TYNDALE_ARCHIVE_SHA256" \
    && git clone https://github.com/openscriptures/HebrewLexicon /tmp/bhf-lexical-sources/HebrewLexicon \
    && git -C /tmp/bhf-lexical-sources/HebrewLexicon checkout "$BHF_HEBREW_LEXICON_REVISION" \
    && git clone https://github.com/openscriptures/strongs /tmp/bhf-lexical-sources/strongs \
    && git -C /tmp/bhf-lexical-sources/strongs checkout "$BHF_STRONGS_REVISION" \
    && git clone https://github.com/openscriptures/morphhb /tmp/bhf-lexical-sources/morphhb \
    && git -C /tmp/bhf-lexical-sources/morphhb checkout "$BHF_OSHB_REVISION" \
    && git clone https://github.com/morphgnt/sblgnt /tmp/bhf-lexical-sources/morphgnt-sblgnt \
    && git -C /tmp/bhf-lexical-sources/morphgnt-sblgnt checkout "$BHF_MORPHGNT_REVISION" \
    && python -m framework.lexical.tools.build_lexicon_database \
        --hebrew /tmp/bhf-lexical-sources/HebrewLexicon/HebrewStrong.xml \
        --greek /tmp/bhf-lexical-sources/strongs/greek/StrongsGreekDictionaryXML_1.4/strongsgreek.xml \
        --output /app/.bhf-seed/lexicon.sqlite \
    && python -m framework.lexical.tools.import_verse_tokens \
        --database /app/.bhf-seed/lexicon.sqlite \
        --oshb-osis-dir /tmp/bhf-lexical-sources/morphhb/wlc \
        --source-name OSHB \
        --source-url https://github.com/openscriptures/morphhb \
        --revision "$BHF_OSHB_REVISION" \
        --license "CC BY 4.0" \
        --attribution "Open Scriptures Hebrew Bible Project" \
        --rebuild-tokens \
    && python -m framework.lexical.tools.import_verse_tokens \
        --database /app/.bhf-seed/lexicon.sqlite \
        --morphgnt-dir /tmp/bhf-lexical-sources/morphgnt-sblgnt \
        --source-name "MorphGNT SBLGNT" \
        --source-url https://github.com/morphgnt/sblgnt \
        --revision "$BHF_MORPHGNT_REVISION" \
        --license "Morphology CC BY-SA 3.0; SBLGNT text subject to SBLGNT EULA" \
        --attribution "Tauber, J. K., ed. (2017) MorphGNT: SBLGNT Edition" \
    && python -m framework.lexical.tools.validate_lexicon /app/.bhf-seed/lexicon.sqlite \
    && python -m framework.lexical.tools.smoke_lexicon --database /app/.bhf-seed/lexicon.sqlite \
    && rm -rf /tmp/bhf-lexical-sources /tmp/bhf-commentary \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /app/.bhf/sessions /app/.bhf/exports /app/.bhf-data/sessions \
    && python -m framework.canonical_library build-db --output /app/.bhf/ckl.sqlite \
    && python -m framework.canonical_library verify-db --database /app/.bhf/ckl.sqlite --skip-fingerprint \
    && chown -R bhf:bhf /app

USER bhf

EXPOSE 8080

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "bhf_web.app:app", "--host", "0.0.0.0", "--port", "8080"]
