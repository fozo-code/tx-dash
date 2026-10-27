# tx-dash installer for Windows (run from CMD or PowerShell)
$raw = "https://raw.githubusercontent.com/fozo-code/tx-dash/main"
$dir = Join-Path $HOME ".txdash"
$bin = Join-Path $dir "bin"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$py = $null
foreach ($c in "py", "python") {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    Write-Host "Python not found. Install it first:  winget install Python.Python.3.12"
    return
}
$pyExe = (& $py -c "import sys; print(sys.executable)").Trim()

New-Item -ItemType Directory -Force -Path $bin | Out-Null
Invoke-WebRequest "$raw/txdash.py" -OutFile "$dir\txdash.py" -UseBasicParsing

# command shim so `txdash` works in CMD and PowerShell
Set-Content -Path "$bin\txdash.cmd" -Encoding ASCII -Value "@echo off`r`n`"$pyExe`" `"%USERPROFILE%\.txdash\txdash.py`" %*"

$p = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $p) { $p = "" }
if (($p -split ";") -notcontains $bin) {
    [Environment]::SetEnvironmentVariable("Path", ($p.TrimEnd(";") + ";" + $bin).TrimStart(";"), "User")
}

Write-Host ""
Write-Host "tx-dash installed. Close this window, open a new CMD and run:  txdash"
