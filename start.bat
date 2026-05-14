@echo off
echo Starting KOLA AI API...
cd /d %~dp0
python model.py
python -m uvicorn api:app --host 0.0.0.0 --port 8000
pause
