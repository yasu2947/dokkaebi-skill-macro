# EXE 빌드 (프로젝트 루트에서 실행)
#   .\.venv\Scripts\Activate.ps1
#   pip install -r requirements-dev.txt
#   .\build_exe.ps1
#
# OneDrive/백신에서 build 잠금 시: .\build_exe.ps1 -NoClean
# PyInstaller onefile은 시작 시 잠깐의 창 깜빡임이 생기기 쉬움. 완화하려면 --onedir 로
# dist\DokkaebiSkillMacro\ 폴더 배포를 검토(동일 exe_entry.py, PyInstaller 문서 참고).
#
# 결과: dist\DokkaebiSkillMacro.exe (콘솔 없음, GUI만)
# 오류 확인용 콘솔 빌드: 아래 $useConsole = $true

param(
  [switch]$NoClean
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$useConsole = $false
$windowArg = if ($useConsole) { "--console" } else { "--windowed" }

# --onefile: EXE 하나만 배포. 첫 실행 시 %TEMP%에 압축 해제 후 시작.
# 스플래시 스피너가 초기화 시간을 자연스럽게 가림.
$bundleMode = "--onefile"

# 실행 중이면 exe 잠금 → Permission denied 방지
Get-Process -Name "DokkaebiSkillMacro" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

$contentsDir = Join-Path $root "contents"

$fontDir = Join-Path $contentsDir "font"
if (-not (Test-Path $fontDir)) {
  throw "번들 폰트 폴더가 없습니다: $fontDir"
}

$imgDir = Join-Path $contentsDir "images"
$yasuPng = Join-Path $imgDir "yasu.png"
if (-not (Test-Path $yasuPng)) {
  throw "로고 PNG가 없습니다: $yasuPng"
}

& $py -m pip install "Pillow>=10" -q
$icoPath = Join-Path $imgDir "yasu.ico"
& $py (Join-Path $root "scripts\png_to_ico.py") $yasuPng $icoPath

# OneDrive/백신 잠금 대비: dist + build 폴더를 미리 직접 삭제
# (PyInstaller --clean 은 localpycs 잠금 시 PermissionError로 빌드 중단 → 사용 안 함)
$distExe  = Join-Path $root "dist\DokkaebiSkillMacro.exe"
$distDir  = Join-Path $root "dist\DokkaebiSkillMacro"
$buildDir = Join-Path $root "build\DokkaebiSkillMacro"

foreach ($d in @($distExe, $distDir, $buildDir)) {
  if (Test-Path $d) {
    Write-Host "삭제 중: $d"
    Remove-Item -Path $d -Recurse -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
  }
}

$cleanArgs = @()  # --clean 제거 (위에서 수동 삭제)

& $py -m PyInstaller `
  @cleanArgs `
  --noconfirm `
  $bundleMode `
  $windowArg `
  --name "DokkaebiSkillMacro" `
  --paths "$root" `
  --icon $icoPath `
  --hidden-import "PyQt6.QtCore" `
  --hidden-import "PyQt6.QtGui" `
  --hidden-import "PyQt6.QtWidgets" `
  --hidden-import "PyQt6.QtMultimedia" `
  --hidden-import "PyQt6.QtMultimediaWidgets" `
  --hidden-import "cv2" `
  --hidden-import "numpy" `
  --hidden-import "mss" `
  --add-data "$(Join-Path $contentsDir 'font');contents/font" `
  --add-data "$(Join-Path $contentsDir 'images');contents/images" `
  (Join-Path $root "exe_entry.py")

Write-Host "완료: $root\dist\DokkaebiSkillMacro.exe  (onefile 모드 — EXE 단독 배포 가능)"
