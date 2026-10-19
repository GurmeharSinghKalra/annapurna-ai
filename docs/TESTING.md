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
4. Open the guest workspace directly; no farmer account is required.
5. Save a recommendation and check Saved Plans; use the clear-data control to verify it is device-local.
6. Create a Season Finance plan and confirm its revenue matches yield × displayed price.
7. Click Report and confirm a text report downloads.
8. Upload a valid PNG, JPEG, or WebP crop image in Crop Disease Detection.
9. Ask the advisor a question after creating a finance plan and confirm the finance context is linked.
10. Use System refresh buttons.
11. After one successful online load, use browser offline mode and reload a non-data page to confirm
    the app shell remains available; API-backed results should remain source-labelled rather than stale-cached.

## Manual Backend Test URLs

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/crops
http://127.0.0.1:8000/admin/summary
http://127.0.0.1:8000/integrations/status
```
