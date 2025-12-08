#!/bin/bash

python3 rutube_worker.py &

uvicorn main:app --host 0.0.0.0 --port 8000
