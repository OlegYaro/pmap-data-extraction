# Runbook: extraction on AWS (dev)

Stacks: `pmap-dev-network`, `pmap-dev-data`, `pmap-dev-extraction` (templates in `infra/`).
Region `eu-north-1`. Run everything from the repo root. A new, empty account: project doc "Инструкция по деплою".

## 1. Deploy main by hand

```bash
aws login
git checkout main && git pull
make deploy
make aws-smoke
```

`deploy` = image of HEAD (tag = short commit, built once) → stack `DesiredCount=0` → `alembic upgrade head` → `DesiredCount=1` → all three services running.

- The powiat in progress is lost; the queue in Redis stays and continues after the start.
- Failed migration → services stay stopped: `make aws-logs SINCE=30m`, fix, deploy again.

## 2. Database and Redis

```bash
brew install --cask session-manager-plugin     # once

make tunnel-db        # 127.0.0.1:15432
make tunnel-redis     # 127.0.0.1:16379
make aws-db-password

psql "postgresql://pmap_admin@127.0.0.1:15432/extraction?sslmode=require"
redis-cli -p 16379 LLEN taskiq          # powiats waiting in the queue
```

Use `127.0.0.1`, not `localhost`. SSL is required. GUI clients may hang on the tunnel; use psql.
The tunnels go through the api container: they stop on every deploy.

## 3. CI/CD

```
PR        -> checks: ruff, alembic upgrade head, pytest on Postgres
push main -> checks -> deploy (GitHub machine): make deploy
```

GitHub signs in to AWS as the IAM user `pmap-dev-github-deploy` with access keys from GitHub Secrets
(OIDC is blocked by the account's SCP). Once:

```bash
aws iam create-user --user-name pmap-dev-github-deploy
aws iam attach-user-policy --user-name pmap-dev-github-deploy \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
aws iam create-access-key --user-name pmap-dev-github-deploy   # shown only once
```

GitHub → Settings → Secrets and variables → Actions → **Secrets** → `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`.

New key (leaked, or once in a while):

```bash
aws iam list-access-keys --user-name pmap-dev-github-deploy
aws iam create-access-key --user-name pmap-dev-github-deploy   # update both secrets
aws iam delete-access-key --user-name pmap-dev-github-deploy --access-key-id <OLD_ID>
```

Run: Actions → ci → Run workflow → `main`, or merge a PR into `main`.

| Error | Fix |
| --- | --- |
| deploy job skipped | not `main`, or a pull request |
| `Credentials could not be loaded` | secrets missing or misspelled |
| `InvalidClientTokenId` / `SignatureDoesNotMatch` | wrong or deleted key: create a new one, update both secrets |

## 4. When something fails

```bash
make aws-check
make aws-logs SINCE=1h
aws cloudformation describe-stack-events --stack-name pmap-dev-extraction \
  --query "StackEvents[?contains(ResourceStatus,'FAILED')].[LogicalResourceId,ResourceStatusReason]" --output table
```

| Error | Cause |
| --- | --- |
| `CannotPullContainerError` | no image with this tag in ECR |
| `exec format error` | image not built for `linux/amd64` |
| exit code 137 | out of memory: stack parameter `WorkerMemory=4096` |
| API not reachable | home IP changed: redeploy `pmap-dev-network` with the new `AdminCidr` |
