# Installer Assets

This folder holds source and final assets used by the Windows installer.

Required before building `A2SB-Restorer-Setup.exe`:

- `app-icon.svg`: editable source icon.
- `app.ico`: generated transparent Windows icon used by the installed app and launcher.
- `setup.ico`: generated transparent icon variant kept for release checks; the installer uses `app.ico` because it matches the installed app/window icon.

Generate or refresh both `.ico` files with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\generate_icon.ps1
```

Do not build the public installer with the default Inno Setup icon.
