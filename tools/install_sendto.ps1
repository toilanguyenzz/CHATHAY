<# 
  Read AI - Cai dat cong cu toi uu cho Windows
  1. "Send To" menu: Chuot phai file bat ky -> Read AI
  2. Desktop shortcut: Mo trang Upload Portal nhanh
  3. Hotkey shortcut: Win+R -> readai -> Enter
#>

$API_URL = "https://chathay-production.up.railway.app"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Read AI - Cai dat cong cu PC" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# --- B1: Tao thu muc app ---
$appDir = Join-Path $env:APPDATA "ReadAI"
if (-not (Test-Path $appDir)) { New-Item -ItemType Directory -Path $appDir | Out-Null }

# --- B2: Tao script xu ly file (cho Send To) ---
$summarizeScript = @'
param([string]$FilePath)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Net.Http

if (-not $FilePath -or -not (Test-Path $FilePath)) {
    [System.Windows.Forms.MessageBox]::Show("Khong tim thay file!", "Read AI", 0, 48)
    exit
}

$fileName = [System.IO.Path]::GetFileName($FilePath)
$ext = [System.IO.Path]::GetExtension($FilePath).ToLower()
$allowed = @(".pdf",".docx",".doc",".jpg",".jpeg",".png",".gif",".bmp",".webp")

if ($ext -notin $allowed) {
    [System.Windows.Forms.MessageBox]::Show("Chi ho tro: PDF, Word, Anh", "Read AI", 0, 48)
    exit
}

try {
    $client = New-Object System.Net.Http.HttpClient
    $client.Timeout = [TimeSpan]::FromSeconds(120)
    $form = New-Object System.Net.Http.MultipartFormDataContent
    $fs = [System.IO.File]::OpenRead($FilePath)
    $sc = New-Object System.Net.Http.StreamContent($fs)
    $form.Add($sc, "file", $fileName)
    $resp = $client.PostAsync("APIURL/api/summarize", $form).Result
    $body = $resp.Content.ReadAsStringAsync().Result
    $fs.Close()
    $client.Dispose()
    $data = $body | ConvertFrom-Json

    if ($data.error) {
        [System.Windows.Forms.MessageBox]::Show($data.error, "Read AI - Loi", 0, 48)
        exit
    }

    $t = $data.document_title
    $o = $data.overview
    $ph = ""
    foreach ($p in $data.points) {
        $i = $p.index; $ti = $p.title; $b = $p.brief; $d = $p.detail
        $ph += "<div class=c onclick=this.classList.toggle('o')><div class=h><div class=n>$i</div><div class=tt>$ti</div><div class=tg>+</div></div><div class=b>$b</div><div class=d>$d</div></div>"
    }

    $html = "<!DOCTYPE html><html><head><meta charset=UTF-8><title>Read AI</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Segoe UI,sans-serif;background:#0a0e1a;color:#f0f0f5;padding:32px 16px}.w{max-width:680px;margin:0 auto}.logo{text-align:center;font-size:28px;font-weight:800;color:#6c5ce7;margin-bottom:4px}.sub{text-align:center;color:#8892b0;font-size:13px;margin-bottom:24px}.hdr{background:#131829;border:1px solid #2d3555;border-radius:12px;padding:20px;margin-bottom:12px}.dt{font-size:18px;font-weight:700;margin-bottom:6px}.ov{color:#8892b0;font-size:13px;line-height:1.5;padding-left:10px;border-left:3px solid #6c5ce7}.c{background:#131829;border:1px solid #2d3555;border-radius:10px;margin-bottom:8px;cursor:pointer;overflow:hidden}.c:hover{border-color:#6c5ce7}.h{display:flex;align-items:center;gap:10px;padding:14px 16px}.n{width:28px;height:28px;background:#6c5ce7;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0}.tt{font-weight:600;font-size:14px;flex:1}.tg{color:#8892b0;font-size:16px}.b{padding:0 16px 10px;font-size:12px;color:#8892b0}.d{display:none;padding:12px 16px;font-size:13px;line-height:1.6;border-top:1px solid #2d3555}.c.o .d{display:block}.c.o .tg{transform:rotate(45deg)}.fb{text-align:center;color:#8892b0;font-size:11px;margin-top:16px}</style></head><body><div class=w><div class=logo>Read AI</div><div class=sub>Ket qua tom tat</div><div class=hdr><div class=dt>$t</div><div class=ov>$o</div></div>$ph<div class=fb>File: $fileName</div></div></body></html>"

    $outPath = Join-Path $env:TEMP "readai_result.html"
    [System.IO.File]::WriteAllText($outPath, $html, [System.Text.Encoding]::UTF8)
    Start-Process $outPath

} catch {
    [System.Windows.Forms.MessageBox]::Show("Loi: " + $_.Exception.Message, "Read AI", 0, 48)
}
'@

$summarizeScript = $summarizeScript.Replace("APIURL", $API_URL)
$scriptPath = Join-Path $appDir "summarize.ps1"
[System.IO.File]::WriteAllText($scriptPath, $summarizeScript, [System.Text.Encoding]::UTF8)
Write-Host "[OK] Script xu ly file da luu" -ForegroundColor Green

# --- B3: Tao Send To shortcut ---
$sendToDir = [Environment]::GetFolderPath("SendTo")
$sendToLnk = Join-Path $sendToDir "Read AI.lnk"

$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($sendToLnk)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-ExecutionPolicy Bypass -WindowStyle Hidden -File ""$scriptPath"" ""%1"""
$sc.Description = "Tom tat tai lieu bang AI"
$sc.Save()
Write-Host "[OK] Send To shortcut da tao" -ForegroundColor Green

# --- B4: Tao Desktop shortcut mo Web Upload ---
$desktopDir = [Environment]::GetFolderPath("Desktop")
$desktopLnk = Join-Path $desktopDir "Read AI.lnk"

$sc2 = $ws.CreateShortcut($desktopLnk)
$sc2.TargetPath = "$API_URL/upload"
$sc2.Description = "Mo trang Read AI - Keo tha file de tom tat"
$sc2.Save()
Write-Host "[OK] Desktop shortcut da tao" -ForegroundColor Green

# --- B5: Tao alias 'readai' cho Run dialog (Win+R) ---
$regPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\readai.exe"
if (-not (Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
Set-ItemProperty -Path $regPath -Name "(Default)" -Value "cmd.exe"
Set-ItemProperty -Path $regPath -Name "Path" -Value $appDir
# Tao bat file
$batContent = "@echo off`nstart """" ""$API_URL/upload"""
$batPath = Join-Path $appDir "readai.bat"
[System.IO.File]::WriteAllText($batPath, $batContent, [System.Text.Encoding]::ASCII)
Write-Host "[OK] Win+R shortcut 'readai' da tao" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  CAI DAT HOAN TAT!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "3 cach su dung:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  [1] CHUOT PHAI bat ky file nao" -ForegroundColor White
Write-Host "      -> Send to -> Read AI" -ForegroundColor Gray
Write-Host "      -> Tu dong tom tat va hien ket qua" -ForegroundColor Gray
Write-Host ""
Write-Host "  [2] DOUBLE-CLICK icon 'Read AI' tren Desktop" -ForegroundColor White
Write-Host "      -> Keo tha file vao trang web" -ForegroundColor Gray
Write-Host ""
Write-Host "  [3] Bam Win+R, go 'readai', Enter" -ForegroundColor White
Write-Host "      -> Mo nhanh trang Upload Portal" -ForegroundColor Gray
Write-Host ""
