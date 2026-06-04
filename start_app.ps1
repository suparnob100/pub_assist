$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

function Test-PythonCommand {
    param(
        [string]$Command,
        [string[]]$PrefixArgs = @()
    )

    try {
        $testArgs = @($PrefixArgs) + @("-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)")
        & $Command @testArgs *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$pythonCommand = $null
$pythonArgs = @()
$display = ""

if (Test-Path -LiteralPath $venvPython) {
    $pythonCommand = $venvPython
    $display = ".venv\Scripts\python.exe"
} elseif (Test-PythonCommand -Command "py" -PrefixArgs @("-3")) {
    $pythonCommand = "py"
    $pythonArgs = @("-3")
    $display = "py -3"
} elseif (Test-PythonCommand -Command "python") {
    $pythonCommand = "python"
    $display = "python"
} else {
    Write-Host ""
    Write-Host "Python 3.10 or newer was not found."
    Write-Host "Run .\install_app.ps1 first."
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host " Pub Assist"
Write-Host " ----------"
Write-Host " Using: $display"
Write-Host " If dependencies are missing, run .\install_app.ps1 first."
Write-Host ""
Write-Host " Starting server at http://127.0.0.1:7654"
Write-Host " Press Ctrl+C to stop."
Write-Host ""

$uvicornArgs = @($pythonArgs) + @("-m", "uvicorn", "app:app", "--reload", "--host", "127.0.0.1", "--port", "7654")
& $pythonCommand @uvicornArgs
