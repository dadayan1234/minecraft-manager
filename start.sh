#!/bin/bash
echo "Menjalankan FastAPI Minecraft Manager..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000
