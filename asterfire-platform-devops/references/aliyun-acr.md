# Alibaba Cloud ACR notes

Verified against Alibaba Cloud docs on 2026-09-17.

## Defaults for this skill

- Region: 华东1（杭州）`cn-hangzhou`
- Enterprise instance name: `asterfire`
- Namespace: `asterfire`
- Repository: project name, e.g. `proteinmpnn`
- First tag: `1.0.0`

## Enterprise OpenAPI

ACR `cr/2018-12-01` exposes Enterprise-oriented APIs used by this Skill, including:

- `ListInstance`
- `ListInstanceEndpoint`
- `ListRepository`
- `CreateRepository`
- `ListRepoTag`
- `CreateRepoSourceCodeRepo`

`CreateRepository` requires `InstanceId`, `RepoName`, `RepoNamespaceName`, `RepoType`, `Summary`.
`ListRepoTag` requires `InstanceId` and `RepoId`.

Docs:
- https://help.aliyun.com/zh/acr/developer-reference/api-cr-2018-12-01-overview
- https://help.aliyun.com/zh/acr/developer-reference/api-cr-2018-12-01-createrepository
- https://help.aliyun.com/zh/acr/developer-reference/api-cr-2018-12-01-listrepotag
- https://help.aliyun.com/zh/acr/developer-reference/api-cr-2018-12-01-listinstanceendpoint

The implementation uses the official `aliyun` CLI generic RPC command, so credentials remain in the user's configured Alibaba Cloud CLI/RAM environment.

For the Yunxiao backend, when `registry_domain` and an explicit image `tag` are both configured, publishing can delegate push validation to the existing `DockerBuildPushACREE` service connection without requiring a local `aliyun` CLI or RAM AccessKey. In this fallback the ACR repository must already exist or the enterprise namespace must allow repository creation on push. The real Flow job is authoritative: a missing repository or insufficient service-connection permission must stop the release with the returned build error.

## Personal Edition

Official documentation is inconsistent as of 2026-09-17:

- Feature comparison page says Personal Edition does not expose OpenAPI.
- A 2026 change announcement discusses Personal Edition OpenAPI region endpoint behavior.

For safety/compatibility, this Skill **does not depend on Personal Edition resource-management OpenAPI**. Personal Edition is supported through an already-created repository plus:

- local `docker login/tag/push`, or
- Yunxiao Flow ACR Personal build/push service connection.

Docs:
- https://help.aliyun.com/zh/acr/product-overview/differences-between-personal-edition-instances-and-enterprise-edition-instances
- https://help.aliyun.com/zh/acr/product-overview/product-change-announcement-on-change-of-access-point-request-for-acr-personal-edition-openapi-service
