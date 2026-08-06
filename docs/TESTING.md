# Testing Guide

## Automated Checks

From project root:

```powershell
npm run build
```

From backend folder:

```powershell
.\.venv\Scripts\python.exe scripts\train_model.py
.\.venv\Scripts\python.exe -m pytest
```

Docker Compose validation:

```powershell
docker compose config
```

## Manual Frontend Test Checklist

Open:

```text
http://127.0.0.1:5173
```

Test these flows:

1. Change season, soil type, pH, rainfall, budget, and priority.
2. Confirm crop recommendation cards update.
3. Click Sync API and confirm backend status changes.
4. Register a farmer account.
5. Login with the same phone and password.
6. Save a recommendation and check Saved History.
7. Click Report and confirm a text report downloads.
8. Upload an image in Crop Disease Detection.
9. Ask the chatbot a question.
10. Use Admin Console refresh buttons.

## Manual Backend Test URLs

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/crops
http://127.0.0.1:8000/admin/summary
http://127.0.0.1:8000/integrations/status
```
