# Study Vault Sync

BHF keeps notes, highlights, saved studies, and map studies local to the
browser by default. Study Vault Sync lets a person carry those records between
devices without making them server-side BHF account data.

## What synchronizes

The encrypted vault contains user-created notes, highlights, saved studies,
map studies, queued map mutations, offline-pack metadata, and deletion markers.
It does not contain AI credentials, browser encryption keys, service-worker
caches, or downloaded translation content. Cached packs are rebuilt locally
after sync. Imported translations remain device-local because their license may
not permit cloud copying.

Each record has a stable ID and timestamps. A newer record wins; when two
versions have the same timestamp but different content, BHF preserves the
remote version as a clearly marked conflict copy rather than discarding text.
Deletion markers prevent an old device from restoring a deleted note.

## Encryption and recovery

Before upload, BHF serializes the portable records and encrypts them in the
browser with AES-GCM. The key is derived from a passphrase using PBKDF2 with
SHA-256 and 310,000 iterations. The passphrase is never sent to BHF, OneDrive,
or iCloud, and BHF does not retain it after the current action.

Keep the passphrase in a password manager. It cannot be recovered. Export an
encrypted vault periodically before changing browsers, clearing site data, or
disconnecting a provider.

## OneDrive setup

Automatic OneDrive sync is enabled only when the deployment supplies a public
Microsoft Entra application client ID:

```text
BHF_ONEDRIVE_CLIENT_ID=<public application client ID>
BHF_ONEDRIVE_REDIRECT_URI=https://your-bhf-origin/
```

Register the redirect URI exactly as used by the PWA and enable delegated OAuth
authorization-code flow with PKCE. Request `Files.ReadWrite.AppFolder` and
`offline_access`; do not give BHF broad filesystem permissions. BHF writes one
encrypted `bhf-study-vault.bhfvault` file to the app folder. See Microsoft’s
[app-folder documentation](https://learn.microsoft.com/en-us/graph/onedrive-sharepoint-appfolder).

## iCloud setup

iCloud sync uses CloudKit JS and a user’s private CloudKit database. It needs
an Apple Developer CloudKit container with web services enabled, an API token
restricted to the BHF origin, and a deployed private-database record type named
`StudyVault` with a `payload` string field.

```text
BHF_CLOUDKIT_CONTAINER_IDENTIFIER=iCloud.com.example.bhf
BHF_CLOUDKIT_API_TOKEN=<CloudKit web API token>
BHF_CLOUDKIT_ENVIRONMENT=production
```

The API token is browser configuration, not a secret; protect it with CloudKit
allowed-origin restrictions. BHF dynamically loads Apple’s CloudKit JS library
only after iCloud is selected. See [CloudKit JS](https://developer.apple.com/documentation/cloudkitjs)
and [obtaining an iCloud API token](https://developer.apple.com/documentation/CloudKit/obtaining-an-api-token-for-an-icloud-container).

## Apple Notes and Google Keep

**Share notes and studies** sends a readable Markdown/text copy through the
platform share sheet. On Apple devices users can choose Notes; on Android they
can choose Google Keep or another installed notes app. This is an intentional
one-way export: edits made in Apple Notes or Google Keep do not flow back into
BHF and cannot create sync conflicts.

Google Keep is not used as a general consumer sync provider. Its API is aimed
at Google Workspace administration, not a personal cross-device data store.
