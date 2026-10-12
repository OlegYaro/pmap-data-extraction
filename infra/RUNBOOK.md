# Runbook: extraction on AWS (dev)

Stacks: `pmap-dev-network`, `pmap-dev-data`, `pmap-dev-extraction` (templates in `infra/`).
Region `eu-north-1`. Run everything from the repo root. A new, empty account: project doc "Инструкция по деплою".

## 1. Deploy main by hand

```bash
aws login                     # session lasts 12 h
git checkout main && git pull
make deploy
make aws-smoke                # only from AdminCidr (your IP)
```

`deploy` = image of HEAD (tag = short commit, built once) → stack `DesiredCount=0` → `alembic upgrade head` → `DesiredCount=1` → all three services running.

- The powiat in progress is lost; the queue in Redis stays and continues after the start.
- Failed migration → services stay stopped: `make aws-logs SINCE=30m`, fix, deploy again.

## 2. Database and Redis

```bash
brew install --cask session-manager-plugin     # once

make tunnel-db        # 127.0.0.1:15432, keep the tab open
make tunnel-redis     # 127.0.0.1:16379, keep the tab open
make aws-db-password

psql "postgresql://pmap_admin@127.0.0.1:15432/extraction?sslmode=require"
redis-cli -p 16379 LLEN taskiq          # powiats waiting in the queue
```

Use `127.0.0.1`, not `localhost`. SSL is required. GUI clients may hang on the tunnel; use psql.
The tunnels go through the api container: they stop on every deploy.

## 3. When something fails

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
