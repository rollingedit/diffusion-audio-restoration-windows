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

function New-IconBitmap {
    param([int]$Size)

    $bitmap = New-Object System.Drawing.Bitmap $Size, $Size, ([System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.Clear([System.Drawing.Color]::Transparent)

    $scale = $Size / 256.0
    $bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
        (New-Object System.Drawing.Rectangle 0, 0, $Size, $Size),
        [System.Drawing.Color]::FromArgb(255, 32, 139, 120),
        [System.Drawing.Color]::FromArgb(255, 42, 92, 170),
        45
    )
    $graphics.FillEllipse($bgBrush, [int](4 * $scale), [int](4 * $scale), [int](248 * $scale), [int](248 * $scale))

    $ringPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(230, 245, 244, 238)), ([single](10 * $scale))
    $graphics.DrawEllipse($ringPen, [int](25 * $scale), [int](25 * $scale), [int](206 * $scale), [int](206 * $scale))

    $wavePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 255, 255, 255)), ([single](12 * $scale))
    $wavePen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $wavePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $points = @(
        (New-Object System.Drawing.Point ([int](54 * $scale)), ([int](136 * $scale))),
        (New-Object System.Drawing.Point ([int](82 * $scale)), ([int](96 * $scale))),
        (New-Object System.Drawing.Point ([int](110 * $scale)), ([int](160 * $scale))),
        (New-Object System.Drawing.Point ([int](146 * $scale)), ([int](84 * $scale))),
        (New-Object System.Drawing.Point ([int](178 * $scale)), ([int](142 * $scale))),
        (New-Object System.Drawing.Point ([int](204 * $scale)), ([int](112 * $scale)))
    )
    $graphics.DrawCurve($wavePen, $points, 0.45)

    $textBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(245, 255, 255, 255))
    $font = New-Object System.Drawing.Font "Segoe UI", ([single](44 * $scale)), ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $graphics.DrawString("A2", $font, $textBrush, (New-Object System.Drawing.RectangleF 0, ([single](148 * $scale)), $Size, ([single](70 * $scale))), $format)

    $graphics.Dispose()
    $bgBrush.Dispose()
    $ringPen.Dispose()
    $wavePen.Dispose()
    $textBrush.Dispose()
    $font.Dispose()
    $format.Dispose()
    return $bitmap
}

function ConvertTo-DibBytes {
    param([System.Drawing.Bitmap]$Bitmap)
    $width = $Bitmap.Width
    $height = $Bitmap.Height
    $xorStride = $width * 4
    $andStride = [int]([Math]::Ceiling($width / 32.0) * 4)
    $pixelBytes = [byte[]]::new([int]($xorStride * $height))
    $maskBytes = [byte[]]::new([int]($andStride * $height))

    for ($y = 0; $y -lt $height; $y++) {
        $sourceY = $height - 1 - $y
        for ($x = 0; $x -lt $width; $x++) {
            $color = $Bitmap.GetPixel($x, $sourceY)
            $pixelOffset = ($y * $xorStride) + ($x * 4)
            if ($color.A -lt 128) {
                $pixelBytes[$pixelOffset] = 120
                $pixelBytes[$pixelOffset + 1] = 139
                $pixelBytes[$pixelOffset + 2] = 32
            } else {
                $pixelBytes[$pixelOffset] = $color.B
                $pixelBytes[$pixelOffset + 1] = $color.G
                $pixelBytes[$pixelOffset + 2] = $color.R
            }
            $pixelBytes[$pixelOffset + 3] = $color.A
            if ($color.A -lt 128) {
                $maskOffset = ($y * $andStride) + [int][Math]::Floor($x / 8.0)
                $maskBytes[$maskOffset] = $maskBytes[$maskOffset] -bor ([byte](0x80 -shr ($x % 8)))
            }
        }
    }

    $stream = New-Object System.IO.MemoryStream
    try {
        $writer = New-Object System.IO.BinaryWriter $stream
        $writer.Write([UInt32]40)
        $writer.Write([Int32]$width)
        $writer.Write([Int32]($height * 2))
        $writer.Write([UInt16]1)
        $writer.Write([UInt16]32)
        $writer.Write([UInt32]0)
        $writer.Write([UInt32]$pixelBytes.Length)
        $writer.Write([Int32]0)
        $writer.Write([Int32]0)
        $writer.Write([UInt32]0)
        $writer.Write([UInt32]0)
        $writer.Write($pixelBytes)
        $writer.Write($maskBytes)
        $writer.Dispose()
        return ,$stream.ToArray()
    } finally {
        $stream.Dispose()
    }
}

$sizes = @(256, 128, 64, 48, 32, 16)
$images = @()
foreach ($size in $sizes) {
    $bitmap = New-IconBitmap -Size $size
    try {
        $images += [pscustomobject]@{
            Size = $size
            Bytes = [byte[]](ConvertTo-DibBytes -Bitmap $bitmap)
        }
    } finally {
        $bitmap.Dispose()
    }
}

$stream = [System.IO.File]::Create($OutputPath)
try {
    $writer = New-Object System.IO.BinaryWriter $stream
    $writer.Write([UInt16]0)
    $writer.Write([UInt16]1)
    $writer.Write([UInt16]$images.Count)
    $offset = 6 + (16 * $images.Count)
    foreach ($image in $images) {
        $dimension = $image.Size
        if ($dimension -eq 256) {
            $dimension = 0
        }
        $writer.Write([byte]$dimension)
        $writer.Write([byte]$dimension)
        $writer.Write([byte]0)
        $writer.Write([byte]0)
        $writer.Write([UInt16]1)
        $writer.Write([UInt16]32)
        $writer.Write([UInt32]$image.Bytes.Length)
        $writer.Write([UInt32]$offset)
        $offset += $image.Bytes.Length
    }
    foreach ($image in $images) {
        $writer.Write([byte[]]$image.Bytes)
    }
    $writer.Dispose()
} finally {
    $stream.Dispose()
}

Write-Host "Wrote $OutputPath"
