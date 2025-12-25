#!/bin/bash

export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

exec uvicorn main:app --host 0.0.0.0 --port 8002 --log-level ${UVICORN_LOG_LEVEL:-info} --workers ${UVICORN_WORKERS:-2}
