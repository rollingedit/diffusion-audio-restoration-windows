# Installer Assets

This folder holds source and final assets used by the Windows installer.

Required before building `A2SB-Restorer-Setup.exe`:

- `app-icon.svg`: editable source icon.
- `app.ico`: generated Windows icon consumed by Inno Setup through `SetupIconFile=assets\app.ico`.

Generate or refresh `app.ico` with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\generate_icon.ps1
```

Do not build the public installer with the default Inno Setup icon.
