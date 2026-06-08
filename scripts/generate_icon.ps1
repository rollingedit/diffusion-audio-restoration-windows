param(
    [string]$Output = "installer\assets\app.ico"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Resolve-Path (Join-Path $ScriptDir "..")
$OutputPath = Join-Path $AppRoot $Output
$OutputDir = Split-Path -Parent $OutputPath

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Add-Type -AssemblyName System.Drawing

$bitmap = New-Object System.Drawing.Bitmap 256, 256
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::FromArgb(18, 22, 28))

$bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
    (New-Object System.Drawing.Rectangle 0, 0, 256, 256),
    [System.Drawing.Color]::FromArgb(32, 139, 120),
    [System.Drawing.Color]::FromArgb(42, 92, 170),
    45
)
$graphics.FillEllipse($bgBrush, 18, 18, 220, 220)

$ringPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(230, 245, 244, 238)), 10
$graphics.DrawEllipse($ringPen, 38, 38, 180, 180)

$wavePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 255, 255, 255)), 12
$wavePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
$wavePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$points = @(
    (New-Object System.Drawing.Point 54, 136),
    (New-Object System.Drawing.Point 82, 96),
    (New-Object System.Drawing.Point 110, 160),
    (New-Object System.Drawing.Point 146, 84),
    (New-Object System.Drawing.Point 178, 142),
    (New-Object System.Drawing.Point 204, 112)
)
$graphics.DrawCurve($wavePen, $points, 0.45)

$textBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(245, 255, 255, 255))
$font = New-Object System.Drawing.Font "Segoe UI", 44, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
$format = New-Object System.Drawing.StringFormat
$format.Alignment = [System.Drawing.StringAlignment]::Center
$graphics.DrawString("A2", $font, $textBrush, (New-Object System.Drawing.RectangleF 0, 148, 256, 70), $format)

$iconHandle = $bitmap.GetHicon()
try {
    $icon = [System.Drawing.Icon]::FromHandle($iconHandle)
    $stream = [System.IO.File]::Create($OutputPath)
    try {
        $icon.Save($stream)
    } finally {
        $stream.Dispose()
        $icon.Dispose()
    }
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    $bgBrush.Dispose()
    $ringPen.Dispose()
    $wavePen.Dispose()
    $textBrush.Dispose()
    $font.Dispose()
    $format.Dispose()
}

Write-Host "Wrote $OutputPath"
