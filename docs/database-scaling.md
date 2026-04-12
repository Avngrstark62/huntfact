# Database Connection Scaling Guide

## Current Architecture
- **FastAPI Server**: 1 instance × 10 connections = 10 connections
- **Worker Processes**: Multiple instances × 10 connections each
- **Pool Config**: `pool_size=10, max_overflow=20` per process

## Connection Limits
- PostgreSQL default: 100 max connections
- MySQL default: 151 max connections
- Current setup with 5 workers: ~60 connections (60% capacity)

## When to Move to PgBouncer

| Metric | Threshold | Action |
|--------|-----------|--------|
| Total Connections | > 70 connections | Implement PgBouncer |
| Worker Processes | > 20 instances | Implement PgBouncer |
| RPS (Requests/sec) | > 100 req/sec | Monitor closely; > 500 = Mandatory |
| DB Process Count | `SELECT count(*) FROM pg_stat_activity` > 75 | Implement PgBouncer |

## Current Status
⚠️ **At Edge**: With 5 workers + 1 API = 60 connections. Plan PgBouncer before scaling beyond 10 workers.

## PgBouncer Setup (Brief)
Install (`apt-get install pgbouncer`), edit config (point to DB), update connection strings (localhost:6432), restart. ~30 mins total. Reduces actual DB connections by 80-90% through intelligent pooling.

## Recommendation
Plan implementation now if scaling to 10+ workers is expected. Delay until threshold hit if staying small (< 5 workers).
