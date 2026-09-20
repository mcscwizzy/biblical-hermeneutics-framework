# Docker Installation and Operations

Docker is the recommended local BHF installation. The image contains the web
application, agent, framework modules, bundled Bible data, and generated CKL,
lexical, and Tyndale commentary databases. During the image build it downloads
the checksum-pinned Tyndale archive and lexical sources, then validates each
generated database.

`docker-compose.yml` runs the deterministic BHF web application. Conversational
follow-up is handed to the external assistant configured by
`BHF_ASSISTANT_URL`.

## Prerequisites

- Git.
- Docker Desktop, or Docker Engine with the Compose v2 plugin.
- Enough time and disk space for the first lexical database build. Later builds
  can reuse Docker's build cache.

Confirm that Compose is available:

```bash
docker compose version
```

## Install BHF

Clone and configure the repository:

```bash
git clone https://github.com/mcscwizzy/biblical-hermeneutics-framework.git
cd biblical-hermeneutics-framework
cp .env.example .env
```

Build and start BHF:

```bash
docker compose up -d --build
```

Check the container and application:

```bash
docker compose ps
docker compose logs --tail=100 bhf-web
curl http://localhost:8080/api/health
```

Open <http://localhost:8080>. No provider or API key setup is required. Use
**Ask BHF** in the reader when you want to continue with the external assistant.

## Configuration

The most useful `.env` settings are:

| Variable | Default | Purpose |
|---|---|---|
| `BHF_HTTP_PORT` | `8080` | Host port for the BHF website/API. |
| `BHF_ASSISTANT_URL` | current BHF assistant | External destination opened by Ask BHF. |
| `BHF_DATA_DIR` | `.bhf-data` outside the image | Shared directory for writable runtime state. |
| `BHF_JOB_DB_PATH` | `$BHF_DATA_DIR/jobs.sqlite` | Explicit override for durable background-job state. |
| `BHF_STUDY_DB_PATH` | `$BHF_DATA_DIR/study.sqlite` | Explicit override for server study data. |
| `BHF_COMMENTARY_DB_PATH` | `$BHF_DATA_DIR/commentary.sqlite` | Explicit override for commentary data. |
| `BHF_TRANSLATIONS_PATH` | `$BHF_DATA_DIR/translations` | Explicit override for transient/server-installed translation data. |
| `BHF_READER_SETTINGS_PATH` | `$BHF_DATA_DIR/reader-settings.json` | Explicit override for reader defaults. |
| `BHF_WEB_CONFIG_PATH` | `$BHF_DATA_DIR/web-config.json` | Explicit override for local web defaults. |
| `BHF_MEMORY_ENABLED` | `false` | Enables local session-memory files. |
| `BHF_LEXICAL_SEED_POLICY` | `refresh` in Compose | `refresh`, `missing`, or `none`. |
| `BHF_COMMENTARY_SEED_POLICY` | `refresh` in Compose | `refresh`, `missing`, or `none` for the Tyndale database. |

The legacy `BHF_PROFILE` and `BHF_ANSWER_MODE` values remain accepted for
compatibility but no longer change the unified runtime answer format.

Do not commit `.env`, `.bhf/`, API keys, or private translation files.

## Persistent data

Both app stacks mount the repository's `.bhf/` directory at
`/app/.bhf-data`:

| Host path | Purpose |
|---|---|
| `.bhf/lexicon.sqlite` | Generated lexical and verse-token database. |
| `.bhf/commentary.sqlite` | Generated Tyndale Open Study Notes database. |
| `.bhf/study.sqlite` | Notes, highlights, saved studies, sources, and other server study data. |
| `.bhf/translations/` | Server-installed translation data and metadata. |
| `.bhf/web-config.json` | Optional local web defaults. |

The generated CKL database stays inside the image at `/app/.bhf/ckl.sqlite`.
Do not change the mount to `/app/.bhf`; doing so hides that database.

On every container start, the entrypoint applies current study-database
migrations to `.bhf/study.sqlite` before Uvicorn starts. This includes the
reviewed archaeology records, Scripture links, and media metadata introduced
by an image update; no manual migration command is required after rebuilding.

PWA data is separate. Each browser profile stores offline packs, device-imported
translations, notes, highlights, and saved studies in IndexedDB and Cache
Storage. Back up browser data with the PWA's **Export offline data** action.

## Railway public beta

The current Railway beta supports exactly **one service replica** with a
persistent Railway volume mounted at `/data`. Set:

```dotenv
BHF_DATA_DIR=/data
```

This resolves the asynchronous job database to `/data/jobs.sqlite`, study data
to `/data/study.sqlite`, and commentary data to `/data/commentary.sqlite`.
Explicit path settings still take precedence; for example, a deployment may
instead set:

```dotenv
BHF_JOB_DB_PATH=/data/jobs.sqlite
BHF_STUDY_DB_PATH=/data/study.sqlite
```

The Railway volume must be writable by the image's `bhf` user (UID/GID 1000).
Configure volume ownership or permissions in Railway if necessary; do not use
world-writable `chmod 777` permissions.

The SQLite `AskJobStore` uses WAL mode and a busy timeout and is appropriate for
this single-instance beta. Multi-replica deployments are not supported because
each replica would require an external shared job store.

## Lexical image build

The Dockerfile clones pinned revisions of HebrewLexicon, Open Scriptures
Strong's, OSHB, and MorphGNT SBLGNT. It builds dictionaries, imports Hebrew and
Greek verse tokens, validates the database, and stores the seed at
`/app/.bhf-seed/lexicon.sqlite`.

Compose defaults to `BHF_LEXICAL_SEED_POLICY=refresh`, so each container start
copies the image seed to `.bhf/lexicon.sqlite`. Set `missing` to preserve an
existing host database, or `none` to disable copying.

Pinned revisions are declared in `.env.example`, the Compose build arguments,
and the Dockerfile. Override them only for an intentional source refresh:

```bash
BHF_HEBREW_LEXICON_REVISION=<commit> \
BHF_STRONGS_REVISION=<commit> \
BHF_OSHB_REVISION=<commit> \
BHF_MORPHGNT_REVISION=<commit> \
docker compose build bhf-web
```

## Tyndale image build

The Dockerfile downloads the official Tyndale Open Study Notes archive, checks
its SHA-256, imports it with strict qualification, and runs `check-tyndale`
before storing the result as `/app/.bhf-seed/commentary.sqlite`. The default
archive URL and checksum are declared in `.env.example`, the Compose build
arguments, and the Dockerfile. Override both together only when intentionally
refreshing the source:

```bash
BHF_TYNDALE_ARCHIVE_URL=<official-archive-url> \
BHF_TYNDALE_ARCHIVE_SHA256=<sha256> \
docker compose build bhf-web
```

Compose copies the validated image seed to `.bhf/commentary.sqlite` on startup.
Set `BHF_COMMENTARY_SEED_POLICY=missing` to preserve a database imported locally
with `framework.commentary import-tyndale`; set it to `none` to disable image
seeding. The standalone importer remains local-only and does not download or
scrape a source archive.

## Routine operations

Stop without deleting application data or images:

```bash
docker compose down
```

Start existing containers again:

```bash
docker compose up -d
```

Rebuild after pulling source changes:

```bash
git pull --ff-only
docker compose up -d --build
```

Follow app logs:

```bash
docker compose logs -f bhf-web
```

Change the host port by editing `.env`:

```dotenv
BHF_HTTP_PORT=8081
```

Then recreate the stack and open <http://localhost:8081>.

## Reset data

Stopping containers does not delete `.bhf/`.

To reset the Docker lexical database without deleting other study data, stop
the stack, delete `.bhf/lexicon.sqlite`, and start with the default `refresh` or
`missing` seed policy. The entrypoint recreates it from the image seed.

Browser offline data is not removed by Docker commands. Use **Clear offline
cache** for rebuildable caches, **Export offline data** before a reset, or the
browser's site-data controls for a full browser-side removal.

## Uninstall

Choose the level that matches what you want to remove.

Remove the default stack's containers, network, and locally built image while
keeping `.bhf/` data:

```bash
docker compose down --rmi local --remove-orphans
```

For a complete local data purge, first export anything you need from the PWA,
stop the applicable stack, and then remove the exact repository-local data
directory:

```bash
rm -rf -- .bhf
```

That last command permanently deletes BHF's local databases, translations,
sessions, and server-side study records. Browser data must still be removed
from that browser's site-data settings. Finally, delete the cloned repository
directory if you no longer want the source tree.

## LAN and public access

Another trusted device on the LAN can open
`http://YOUR_HOST_LAN_IP:8080`, subject to the host firewall. Ask BHF still
requires internet access to open its external destination.

The supplied stack has no accounts, authentication, rate limiting, or public
internet hardening. Do not publish port 8080 directly. Put a public deployment
behind trusted HTTPS plus your own access control, monitoring, backups, and
abuse protections.

## Troubleshooting

**The health check fails:** run `docker compose ps` and
`docker compose logs --tail=200 bhf-web`. A first build can take time while the
lexical sources are cloned and imported.

**The port is already in use:** change `BHF_HTTP_PORT` in `.env` and recreate
the stack.

**CKL routes fail after changing volumes:** restore the documented
`./.bhf:/app/.bhf-data` mount so `/app/.bhf/ckl.sqlite` remains visible.
