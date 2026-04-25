# PerfSense — Stopping the Full System

## Stop All Services

### Terminal 1 — Inference Service (FastAPI)
Press `Ctrl + C` in the terminal running `06_inference_service.py`.

### Terminal 2 — Backend API (Node/Express)
Press `Ctrl + C` in the terminal running `node backend/src/app.js`.

### Terminal 3 — Dashboard (Vite)
Press `Ctrl + C` in the terminal running `npm run dev`.

---

## Force Kill by Port (if Ctrl+C doesn't work)

Find and kill processes by port number on Windows:

```bat
# Kill inference service (port 8000)
for /f "tokens=5" %a in ('netstat -ano ^| findstr ":8000 "') do taskkill /PID %a /F

# Kill backend API (port 3001)
for /f "tokens=5" %a in ('netstat -ano ^| findstr ":3001 "') do taskkill /PID %a /F

# Kill dashboard (port 5173)
for /f "tokens=5" %a in ('netstat -ano ^| findstr ":5173 "') do taskkill /PID %a /F
```

Or use npx (if installed):
```bash
npx kill-port 8000 3001 5173
```

---

## Verify All Ports are Free

```bash
netstat -ano | findstr ":8000 :3001 :5173"
# Should return no output if all services are stopped
```

---

## Port Reference

| Service | Port | Process |
|---|---|---|
| Inference Service (FastAPI) | 8000 | `python 06_inference_service.py` |
| Backend API (Node/Express) | 3001 | `node backend/src/app.js` |
| Dashboard (Vite dev server) | 5173 | `npm run dev` |
| Lighthouse test server | 9900 | `http-server` (only during LH runs) |
