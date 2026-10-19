#!/usr/bin/env bash
# AWS commands of the extraction service. Called by make: see infra/RUNBOOK.md.
set -euo pipefail

P=pmap-${PMAP_ENV:-dev}
STACK=$P-extraction
CLUSTER=$P-extraction
export AWS_REGION=${AWS_REGION:-eu-north-1}

die() { echo "$*" >&2; exit 1; }
exported() { aws cloudformation list-exports --query "Exports[?Name=='$1'].Value" --output text; }
api_task() {
	local task
	task=$(aws ecs list-tasks --cluster "$CLUSTER" --service-name api --query 'taskArns[0]' --output text)
	[ "$task" != None ] || die "api is not running"
	echo "$task"
}

update_stack() {
	aws cloudformation deploy --stack-name "$STACK" --template-file infra/extraction.yaml \
		--capabilities CAPABILITY_IAM --no-fail-on-empty-changeset \
		--parameter-overrides ImageTag="$1" DesiredCount="$2"
}

migrate() {
	local task status
	task=$(aws ecs run-task --cluster "$CLUSTER" --launch-type FARGATE \
		--task-definition "$P-extraction-worker" \
		--network-configuration "awsvpcConfiguration={subnets=[$(exported "$P-PublicSubnets")],securityGroups=[$(exported "$P-ExtractionSecurityGroup")],assignPublicIp=ENABLED}" \
		--overrides '{"containerOverrides":[{"name":"app","command":["alembic","upgrade","head"]}]}' \
		--query 'tasks[0].taskArn' --output text)
	echo "migration task ${task##*/}"
	until [ "$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$task" \
		--query 'tasks[0].lastStatus' --output text)" = STOPPED ]; do sleep 10; done
	status=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$task" \
		--query 'tasks[0].[containers[0].exitCode,stoppedReason]' --output text)
	[ "${status%%[[:space:]]*}" = 0 ] || die "migration failed: $status. Logs: make aws-logs"
}

deploy() {
	local tag repo
	[ -z "$(git status --porcelain)" ] || die "commit or stash your changes: the image is tagged with the commit"
	tag=$(git rev-parse --short HEAD)
	repo=$(aws cloudformation describe-stacks --stack-name "$STACK" \
		--query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue" --output text)
	if aws ecr describe-images --repository-name "$STACK" --image-ids imageTag="$tag" >/dev/null 2>&1; then
		echo "image $tag is already in ECR"
	else
		aws ecr get-login-password | docker login --username AWS --password-stdin "${repo%%/*}"
		docker buildx build --platform linux/amd64 -f dockerfile -t "$repo:$tag" --push .
	fi
	update_stack "$tag" 0
	migrate
	update_stack "$tag" 1
}

check() {
	local down
	aws ecs wait services-stable --cluster "$CLUSTER" --services api worker scheduler
	down=$(aws ecs describe-services --cluster "$CLUSTER" --services api worker scheduler \
		--query 'services[?runningCount!=desiredCount || desiredCount==`0`].serviceName' --output text)
	[ -z "$down" ] || die "not running: $down"
	echo "OK: api, worker and scheduler are running"
}

api_url() {
	local task eni ip
	task=$(api_task)
	eni=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$task" \
		--query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" --output text)
	ip=$(aws ec2 describe-network-interfaces --network-interface-ids "$eni" \
		--query 'NetworkInterfaces[0].Association.PublicIp' --output text)
	echo "http://$ip:8000"
}

smoke() {
	local url
	url=$(api_url)
	for _ in $(seq 12); do
		curl -fsS --max-time 5 "$url/health" >/dev/null && break
		sleep 5
	done
	curl -fsS --max-time 5 "$url/health" >/dev/null || die "$url/health does not answer"
	[ "$(curl -s --max-time 5 -o /dev/null -w '%{http_code}' "$url/transactions")" = 401 ] || die "API answers without the key"
	echo "OK: $url"
}

tunnel() {
	local host port local_port task runtime
	case ${1:-} in
	db) host=$(exported "$P-DbHost") port=5432 local_port=15432 ;;
	redis) host=$(exported "$P-RedisHost") port=6379 local_port=16379 ;;
	*) die "usage: $0 tunnel db|redis" ;;
	esac
	task=$(api_task)
	runtime=$(aws ecs describe-tasks --cluster "$CLUSTER" --tasks "$task" \
		--query 'tasks[0].containers[0].runtimeId' --output text)
	echo "127.0.0.1:$local_port -> $host:$port, Ctrl+C to close"
	aws ssm start-session --target "ecs:${CLUSTER}_${task##*/}_${runtime}" \
		--document-name AWS-StartPortForwardingSessionToRemoteHost \
		--parameters "{\"host\":[\"$host\"],\"portNumber\":[\"$port\"],\"localPortNumber\":[\"$local_port\"]}"
}

db_password() {
	aws secretsmanager get-secret-value --secret-id "$(exported "$P-DbMasterSecretArn")" \
		--query SecretString --output text | python3 -c 'import json, sys; print(json.load(sys.stdin)["password"])'
}

case ${1:-} in
deploy | migrate | check | api_url | smoke | db_password) "$1" ;;
tunnel) tunnel "${2:-}" ;;
*) die "usage: $0 deploy|migrate|check|api_url|smoke|tunnel db|redis|db_password" ;;
esac
