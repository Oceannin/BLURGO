[CmdletBinding()]
param(
    [string] $Title = 'BlurGo Window Capture QA',
    [ValidateRange(640, 3840)]
    [int] $Width = 1280,
    [ValidateRange(360, 2160)]
    [int] $Height = 720
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

$form = [System.Windows.Forms.Form]::new()
$form.Text = $Title
$form.ClientSize = [System.Drawing.Size]::new($Width, $Height)
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::Manual
$form.Location = [System.Drawing.Point]::new(80, 80)
$form.BackColor = [System.Drawing.Color]::Black
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$form.MaximizeBox = $false

$form.Add_Paint({
        param($sender, $eventArgs)

        $graphics = $eventArgs.Graphics
        $cell = [int] [Math]::Max(
            32,
            [Math]::Min($sender.ClientSize.Width, $sender.ClientSize.Height) / 10
        )
        for ($y = 0; $y -lt $sender.ClientSize.Height; $y += $cell) {
            for ($x = 0; $x -lt $sender.ClientSize.Width; $x += $cell) {
                $color = if ((($x / $cell) + ($y / $cell)) % 2 -eq 0) {
                    [System.Drawing.Color]::FromArgb(246, 248, 252)
                }
                else {
                    [System.Drawing.Color]::FromArgb(15, 23, 42)
                }
                $brush = [System.Drawing.SolidBrush]::new($color)
                try {
                    $graphics.FillRectangle($brush, $x, $y, $cell, $cell)
                }
                finally {
                    $brush.Dispose()
                }
            }
        }

        $circleSize = [int] ([Math]::Min($sender.ClientSize.Width, $sender.ClientSize.Height) * 0.72)
        $circleX = [int] (($sender.ClientSize.Width - $circleSize) / 2)
        $circleY = [int] (($sender.ClientSize.Height - $circleSize) / 2)
        $redBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(239, 68, 68))
        $blueBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(37, 99, 235))
        try {
            $graphics.FillEllipse($redBrush, $circleX, $circleY, $circleSize, $circleSize)
            $rectWidth = [int] ($sender.ClientSize.Width * 0.15)
            $rectHeight = [int] ($sender.ClientSize.Height * 0.28)
            $graphics.FillRectangle(
                $blueBrush,
                [int] (($sender.ClientSize.Width - $rectWidth) / 2),
                [int] (($sender.ClientSize.Height - $rectHeight) / 2),
                $rectWidth,
                $rectHeight
            )
        }
        finally {
            $redBrush.Dispose()
            $blueBrush.Dispose()
        }
    })

[System.Windows.Forms.Application]::EnableVisualStyles()
[System.Windows.Forms.Application]::Run($form)
