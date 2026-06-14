#!/bin/bash
set -e

NAMESPACE="pastebin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Building backend Docker image ==="
docker build -t pastebin-backend:latest "$ROOT_DIR/backend"

echo ""
echo "=== Applying Kubernetes manifests ==="
kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
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
echo "Backend pods:"
kubectl -n "$NAMESPACE" get pods -l app=pastebin-backend
echo ""
echo "Access via: http://pastebin.local (add to /etc/hosts: <minikube-ip> pastebin.local)"
echo "Or port-forward: kubectl -n $NAMESPACE port-forward svc/pastebin-backend 8000:8000"
