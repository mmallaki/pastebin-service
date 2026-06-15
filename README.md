# Pastebin Service

A Pastebin-like service built with FastAPI, PostgreSQL, Redis, and deployed on Kubernetes.

## Architecture

```
┌───────────────────────────────────────────────────┐
│                   Kubernetes Cluster               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  Nginx   │──│  FastAPI │  │Prometheus│        │
│  │ (proxy)  │  │  Backend │  │+ Grafana │        │
│  └──────────┘  └──────────┘  └──────────┘        │
│       │             │             │                │
│  ┌──────────────────────────────────────────┐     │
│  │              Data Layer                   │     │
│  │  ┌──────────────┐  ┌──────────────┐      │     │
│  │  │ PostgreSQL   │  │    Redis     │      │     │
│  │  │  (Primary)   │  │   (Cache)    │      │     │
│  │  └──────────────┘  └──────────────┘      │     │
│  └──────────────────────────────────────────┘     │
└───────────────────────────────────────────────────┘
```

## Features

- **Paste Management**: Create, read, delete pastes
- **Share Keys**: Short 8-char keys for easy sharing
- **Syntax Highlighting**: 22+ languages via highlight.js
- **Expiration**: 10min, 1hr, 1day, 1week, never
- **View Counts**: Tracked per share key access
- **Rate Limiting**: Redis-based per-IP rate limiting
- **Monitoring**: Prometheus metrics

## Quick Start

```bash
# Development
docker-compose up -d

# Kubernetes
./k8s/deploy.sh
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/pastes | Create a paste |
| GET | /api/v1/pastes/{id} | Get a paste |
| GET | /api/v1/pastes | List pastes (with search, language filter) |
| GET | /api/v1/view/{share_key} | Get paste by share key |
| GET | /api/v1/stats | Paste statistics |
| GET | /api/v1/languages | Supported languages |
| DELETE | /api/v1/pastes/{id} | Delete a paste |
| GET | /health | Health check |
| GET | /metrics | Prometheus metrics |
| GET | /view/{share_key} | Shareable landing page |
