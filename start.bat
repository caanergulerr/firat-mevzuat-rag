@echo off
echo ===================================================
echo Firat Mevzuat RAG - Baslatma Komutu
echo ===================================================

echo [1/2] Arka plan API sunucusu baslatiliyor (Port 8000)...
start "Firat RAG - Backend API" cmd /k "venv\Scripts\python.exe -m uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000"

echo [2/2] Frontend arayuzu baslatiliyor (Port 3000)...
start "Firat RAG - Frontend" cmd /k "venv\Scripts\python.exe -m http.server 3000 --directory frontend"

echo ===================================================
echo Sistem basariyla calistirildi!
echo Tarayicinizda su adrese gidebilirsiniz:
echo http://localhost:3000
echo ===================================================
pause
