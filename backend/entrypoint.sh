#!/bin/sh
set -e
alembic upgrade head
exec uvicorn app:app --host 0.0.0.0 --port "${API_PORT}" --proxy-headers
