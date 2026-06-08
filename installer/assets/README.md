# Installer Assets

This folder holds source and final assets used by the Windows installer.

Required before building `A2SB-Restorer-Setup.exe`:

- `app-icon.svg`: editable source icon.
- `app.ico`: generated Windows icon consumed by Inno Setup through `SetupIconFile=assets\app.ico`.

Generate `app.ico` from `app-icon.svg` with reviewed icon tooling before release. Include common Windows icon sizes such as 16, 24, 32, 48, 64, 128, and 256 px. Do not build the public installer with the default Inno Setup icon.
