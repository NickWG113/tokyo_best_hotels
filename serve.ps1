# Serves this folder at http://localhost:5500 - no Node/Python required.
$ErrorActionPreference = "Stop"
$port = 5500
$root = $PSScriptRoot
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$port/")
try {
  $listener.Start()
} catch {
  Write-Host "Could not bind port $port. Try: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned"
  Write-Host "Or run PowerShell as Administrator once for URL ACL, or change `$port in this script."
  throw
}

function Get-MimeType([string]$path) {
  switch ([System.IO.Path]::GetExtension($path).ToLowerInvariant()) {
    ".html" { return "text/html; charset=utf-8" }
    ".css"  { return "text/css; charset=utf-8" }
    ".js"   { return "application/javascript; charset=utf-8" }
    ".json" { return "application/json; charset=utf-8" }
    ".svg"  { return "image/svg+xml" }
    ".png"  { return "image/png" }
    ".jpg"  { return "image/jpeg" }
    ".jpeg" { return "image/jpeg" }
    ".webp" { return "image/webp" }
    ".ico"  { return "image/x-icon" }
    ".woff" { return "font/woff" }
    ".woff2" { return "font/woff2" }
    default { return "application/octet-stream" }
  }
}

Write-Host ""
Write-Host "  Tokyo Best Hotels - local server" -ForegroundColor Cyan
Write-Host "  Open: http://127.0.0.1:$port/" -ForegroundColor Green
Write-Host "  Root: $root"
Write-Host "  Ctrl+C to stop."
Write-Host ""

while ($listener.IsListening) {
  $ctx = $listener.GetContext()
  $req = $ctx.Request
  $res = $ctx.Response
  try {
    $path = [Uri]::UnescapeDataString($req.Url.AbsolutePath)
    if ($path -eq "/" -or $path -eq "") { $path = "/index.html" }
    $safe = $path.TrimStart("/").Replace("/", [IO.Path]::DirectorySeparatorChar)
    $full = [IO.Path]::GetFullPath((Join-Path $root $safe))
    if (-not $full.StartsWith([IO.Path]::GetFullPath($root), [StringComparison]::OrdinalIgnoreCase)) {
      $res.StatusCode = 403
      $buf = [Text.Encoding]::UTF8.GetBytes("Forbidden")
      $res.OutputStream.Write($buf, 0, $buf.Length)
      continue
    }
    if (Test-Path $full -PathType Leaf) {
      $bytes = [IO.File]::ReadAllBytes($full)
      $res.ContentType = Get-MimeType $full
      $res.ContentLength64 = $bytes.LongLength
      $res.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $res.StatusCode = 404
      $msg = [Text.Encoding]::UTF8.GetBytes(('Not found: ' + $path))
      $res.ContentLength64 = $msg.LongLength
      $res.OutputStream.Write($msg, 0, $msg.Length)
    }
  } finally {
    $res.Close()
  }
}
