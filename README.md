# Pastebin Service

A comprehensive Pastebin-like service built with FastAPI, PostgreSQL, Redis, and deployed on Kubernetes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Kubernetes Cluster                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │  Nginx   │  │  FastAPI │  │ Telegram │  │Prometheus│           │
│  │ Ingress  │──│  Backend │  │   Bot    │  │+ Grafana │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│       │             │             │             │                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Data Layer                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │ PostgreSQL   │  │    Redis     │  │   MinIO/S3   │      │   │
│  │  │  (Primary)   │  │   (Cache)    │  │  (Optional)  │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

- **Paste Management**: Create, read, update, delete pastes
- **Syntax Highlighting**: Support for 100+ languages via Pygments
- **Expiration**: 10min, 1hr, 1day, 1week, never
- **API Access**: RESTful API for programmatic access
- **Rate Limiting**: Redis-based rate limiting
- **Monitoring**: Prometheus metrics + Grafana dashboards
- **Telegram Bot**: System monitoring and alerts

## Quick Start

```bash
# Development
docker-compose up -d

# Production (Kubernetes)
helm install pastebin ./deploy/k8s/helm
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | /api/v1/pastes | Create a paste |
| GET    | /api/v1/pastes/{id} | Get a paste |
| DELETE | /api/v1/pastes/{id} | Delete a paste |
| GET    | /api/v1/pastes | List pastes |
| GET    | /health | Health check |
| GET    | /metrics | Prometheus metrics |

## Documentation

- [API Documentation](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Iran Hosting Guide](docs/iran-hosting.md)
