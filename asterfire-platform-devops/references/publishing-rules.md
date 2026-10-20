# Publishing rules

## Naming

Pipeline: `asterfire-{project}-{artifact}-{version}-{purpose}`.

Example:

`asterfire-proteinmpnn-image-1.0.0-build`

ACR repository defaults to normalized project name.

## Versioning

- no semver tags -> `1.0.0`
- new version -> patch bump of highest `X.Y.Z`
- overwrite -> explicit existing tag is reused unchanged

Non-semver tags such as `latest` are ignored for automatic version selection.

## Dockerfile path

For Codeup builds, Dockerfile must be resolvable relative to repository root, e.g.:

- `Dockerfile`
- `docker/Dockerfile`
- `META/config/Dockerfile`

Local builds may accept an absolute path, but generated Flow config always uses a repository-relative path.

## Credentials

Never write these values to files:

- `ASTERFIRE_TOKEN`
- `YUNXIAO_TOKEN`
- Alibaba Cloud AccessKey ID / Secret
- ACR password
- Codeup/ACR service connection secrets

Only environment variable *names* belong in config.

Use the bundled `.env.example` as the canonical variable list. The CLI automatically loads the nearest `.env` from the project, current working directory, or config directory without overriding variables already exported by the shell. Never package the real `.env`.

For the internal Yunxiao + ACR Enterprise path, the required variables are `ASTERFIRE_TOKEN`, `YUNXIAO_TOKEN`, `YUNXIAO_ORGANIZATION_ID`, `YUNXIAO_CODEUP_SERVICE_CONNECTION`, and `YUNXIAO_ACR_SERVICE_CONNECTION`. `ACR_USERNAME` and `ACR_PASSWORD` are only for the local Docker backend.

## Dry run

Use dry-run before remote mutations. Dry-run prints planned commands/config and must not call ACR, Flow, Adam, docker push, or toolbox upload.
