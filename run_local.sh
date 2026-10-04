#!/usr/bin/env bash
set -e
python -m uvicorn api.index:app --reload
