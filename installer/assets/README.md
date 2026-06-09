# Installer Assets

This folder holds source and final assets used by the Windows installer.

Required before building `A2SB-Restorer-Setup.exe`:

- `app-icon.svg`: editable source icon.
- `app.ico`: generated transparent Windows icon used by the installed app and launcher.
- `setup.ico`: generated setup EXE icon with a shell-safe matte so Explorer does not show an accidental black transparency box.

Generate or refresh both `.ico` files with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\generate_icon.ps1
```

Do not build the public installer with the default Inno Setup icon.
