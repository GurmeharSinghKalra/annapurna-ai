# Windows Portable Package

`build_windows_portable.ps1` creates a friend-ready Windows ZIP at `release/Annapurna-AI-Windows.zip`.

The ZIP contains a PyInstaller-built local server, the compiled React client, the trained starter model, a one-click launcher, a stop script, and a short user guide. The recipient does not need GitHub, Node.js, Python, or Docker.

Build from PowerShell in the project root:

```powershell
.\distribution\build_windows_portable.ps1
```

The portable server listens only on `127.0.0.1:5173`, opens the browser automatically, and stores SQLite data beside the executable. It uses local fallbacks until an optional `.env` file is added with Gemini or OpenWeatherMap credentials.
