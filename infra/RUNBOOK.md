# Runbook: extraction on AWS (dev)

Stacks: `pmap-dev-network`, `pmap-dev-data`, `pmap-dev-extraction`, `pmap-dev-github` (templates in `infra/`).
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
push main -> checks -> deploy: make deploy (+ make aws-smoke on self-hosted)
```

### 3.1 Once, for both ways

1. Roles for GitHub:

   ```bash
   aws cloudformation deploy --stack-name pmap-dev-github --template-file infra/github.yaml \
     --capabilities CAPABILITY_NAMED_IAM
   aws cloudformation describe-stacks --stack-name pmap-dev-github \
     --query "Stacks[0].Outputs[?OutputKey=='DeployRoleArn'].OutputValue" --output text
   ```

   `... already exists` on the OIDC provider: delete the failed stack, add `--parameter-overrides CreateOidcProvider=false`.

2. GitHub → Settings → Environments → New environment `dev` → Deployment branches and tags → Selected branches → `main`.
3. GitHub → Settings → Secrets and variables → Actions → Variables → `AWS_DEPLOY_ROLE_ARN` = ARN from step 1.

### 3.2 Way A: GitHub machine

Nothing else. The `/health` check is skipped: port 8000 is open only to your IP.

### 3.3 Way B: runner on the Mac

1. GitHub → Settings → Actions → General → Fork pull request workflows → **Require approval for all external contributors**.
2. GitHub → Settings → Actions → Runners → New self-hosted runner → macOS, ARM64. Copy the download commands, then:

   ```bash
   mkdir -p ~/actions-runner && cd ~/actions-runner
   # curl ... && tar ...   (from the GitHub page)
   ./config.sh --url https://github.com/OlegYaro/pmap-data-extraction --token <TOKEN> \
     --name macbook --labels pmap-deploy --unattended
   echo "$PATH" > .path        # in a terminal where docker, aws and make work
   ./svc.sh install && ./svc.sh start
   ```

3. Variables → `DEPLOY_RUNNER` = `self-hosted`. Runners page: `macbook` is **Idle**. Docker Desktop must run, the Mac must not sleep.

Back to way A: delete `DEPLOY_RUNNER`.

### 3.4 Run

Actions → ci → Run workflow → `main`, or merge a PR into `main`.

| Error | Fix |
| --- | --- |
| deploy job skipped | `AWS_DEPLOY_ROLE_ARN` not set, or not `main` |
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | environment is not `dev`, or repo name case differs from `GitHubRepo` |
| `Waiting for a runner` | runner offline, Mac asleep, no `pmap-deploy` label |
| `docker` / `aws: command not found` | `.path` of the runner, then `./svc.sh stop && ./svc.sh start` |
| `Cannot connect to the Docker daemon` | start Docker Desktop |
| `aws-smoke` times out | Mac IP is not `AdminCidr` of `pmap-dev-network` |

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
