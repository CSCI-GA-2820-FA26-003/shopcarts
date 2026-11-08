# Docker pushes through the published registry port.
# Kubernetes pulls through the internal k3d registry address.
REGISTRY ?= cluster-registry:5000
REGISTRY_PORT ?= 5000
PUSH_REGISTRY ?= localhost:$(REGISTRY_PORT)

IMAGE_NAME ?= shopcarts
IMAGE_TAG ?= 1.0
IMAGE ?= $(REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
PUSH_IMAGE ?= $(PUSH_REGISTRY)/$(IMAGE_NAME):$(IMAGE_TAG)
PLATFORM ?= "linux/amd64,linux/arm64"

CLUSTER ?= nyu-devops
KUBE_CONTEXT ?= k3d-$(CLUSTER)
NAMESPACE ?= default
HTTP_PORT ?= 8080

KUBECTL = kubectl --context $(KUBE_CONTEXT) --namespace $(NAMESPACE)

.SILENT:

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: all
all: help

##@ Development

.PHONY: clean
clean:	## Removes all dangling build cache
	$(info Removing all dangling build cache..)
	-docker rmi $(IMAGE)
	docker image prune -f
	docker buildx prune -f

.PHONY: install
install: ## Install Python dependencies
	$(info Installing dependencies...)
	sudo pipenv install --system --dev

.PHONY: lint
lint: ## Run the linter
	$(info Running linting...)
	-flake8 service tests --count --select=E9,F63,F7,F82 --show-source --statistics
	-flake8 service tests --count --max-complexity=10 --max-line-length=127 --statistics
	-pylint service tests --max-line-length=127

.PHONY: test
test: ## Run the unit tests
	$(info Running tests...)
	export RETRY_COUNT=1; pytest --pspec --cov=service --cov-fail-under=95 --disable-warnings

.PHONY: run
run: ## Run the service
	$(info Starting service...)
	honcho start

.PHONY: secret
secret: ## Generate a secret hex key
	$(info Generating a new secret key...)
	python3 -c 'import secrets; print(secrets.token_hex())'

##@ Kubernetes

.PHONY: cluster
cluster: ## Create a local k3d cluster with a registry and HTTP ingress port
	k3d cluster create $(CLUSTER) --agents 1 \
		--registry-create cluster-registry:127.0.0.1:$(REGISTRY_PORT) \
		--registry-config config/registries.yaml \
		--port "$(HTTP_PORT):80@loadbalancer" \
		--wait --timeout 180s

.PHONY: cluster-rm
cluster-rm: ## Remove the configured k3d cluster
	k3d cluster delete $(CLUSTER)

.PHONY: import
import: ## Import the image into the local K3D cluster
	$(info Importing $(IMAGE) into k3d cluster $(CLUSTER)...)
	k3d image import --cluster $(CLUSTER) $(IMAGE)

.PHONY: deploy
deploy: ## Deploy PostgreSQL, Flask, and Ingress
	$(KUBECTL) get secret postgres-credentials shopcarts-db-connection -o name
	$(KUBECTL) apply -f k8s/postgres/
	$(KUBECTL) rollout status statefulset/postgres --timeout=180s
	$(KUBECTL) apply -f k8s/deployment.yaml -f k8s/service.yaml
	$(KUBECTL) rollout status deployment/shopcarts --timeout=180s
	$(KUBECTL) apply -f k8s/ingress.yaml

############################################################
# COMMANDS FOR BUILDING THE IMAGE
############################################################

##@ Image Build and Push

.PHONY: init
init: export DOCKER_BUILDKIT=1
init:	## Creates the buildx instance
	$(info Initializing Builder...)
	-docker buildx create --use --name=qemu
	docker buildx inspect --bootstrap

.PHONY: build
build: ## Build the application image for the local platform
	$(info Building $(IMAGE)...)
	docker build --rm --pull --file Dockerfile --tag $(IMAGE) .

.PHONY: push
push: ## Push the image through the published registry port
	$(info Pushing $(PUSH_IMAGE)...)
	docker tag $(IMAGE) $(PUSH_IMAGE)
	docker push $(PUSH_IMAGE)

.PHONY: buildx
buildx: ## Build and push a multi-platform image
	$(info Building $(PUSH_IMAGE) for $(PLATFORM)...)
	docker buildx build --file Dockerfile --pull \
		--platform=$(PLATFORM) --tag $(PUSH_IMAGE) --push .

.PHONY: remove
remove:	## Stop and remove the buildx builder
	$(info Stopping and removing the builder image...)
	docker buildx stop
	docker buildx rm
