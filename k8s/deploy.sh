#!/bin/bash
set -e

NAMESPACE="pastebin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ROOT_DIR/backend/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE not found. Copy .env.example to .env and fill in values."
    exit 1
fi

get_env() {
    grep "^$1=" "$ENV_FILE" | cut -d= -f2
}

echo "=== Building backend Docker image ==="
docker build -t mmallaki13/pastebin-backend:latest "$ROOT_DIR/backend"

echo ""
echo "=== Applying Kubernetes manifests ==="
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"

echo "=== Creating secrets from .env ==="
kubectl -n "$NAMESPACE" create secret generic pastebin-secrets \
    --from-literal=POSTGRES_USER="$(get_env POSTGRES_USER)" \
    --from-literal=POSTGRES_PASSWORD="$(get_env POSTGRES_PASSWORD)" \
    --from-literal=POSTGRES_DB="$(get_env POSTGRES_DB)" \
    --from-literal=SECRET_KEY="$(get_env SECRET_KEY)" \
    --from-literal=POSTGRES_SERVER=pastebin-postgres \
    --from-literal=REDIS_HOST=pastebin-redis \
    --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "$SCRIPT_DIR/config.yaml"
kubectl apply -f "$SCRIPT_DIR/postgres.yaml"
kubectl apply -f "$SCRIPT_DIR/redis.yaml"
kubectl apply -f "$SCRIPT_DIR/backend.yaml"
kubectl apply -f "$SCRIPT_DIR/ingress.yaml"

echo ""
echo "=== Waiting for deployments ==="
kubectl -n "$NAMESPACE" rollout status deployment/pastebin-postgres --timeout=60s
kubectl -n "$NAMESPACE" rollout status deployment/pastebin-redis --timeout=60s
kubectl -n "$NAMESPACE" rollout status deployment/pastebin-backend --timeout=60s

echo ""
echo "=== Deployment complete ==="
kubectl -n "$NAMESPACE" get pods
echo ""
echo "Port-forward: kubectl -n $NAMESPACE port-forward svc/pastebin-backend 8000:8000"
