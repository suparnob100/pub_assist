$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

Write-Host ""
Write-Host " Pub Assist installer"
Write-Host " --------------------"
Write-Host ""

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

function Find-Python {
    if (Test-PythonCommand -Command "py" -PrefixArgs @("-3")) {
        return [pscustomobject]@{ Command = "py"; Args = @("-3"); Display = "py -3" }
    }
    if (Test-PythonCommand -Command "python") {
        return [pscustomobject]@{ Command = "python"; Args = @(); Display = "python" }
    }
    return $null
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]$Python,
        [Parameter(ValueFromRemainingArguments = $true)][string[]]$PythonArgs
    )

    $args = @($Python.Args) + @($PythonArgs)
    & $Python.Command @args
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($Python.Display) $($PythonArgs -join ' ')"
    }
}

$python = Find-Python
if ($null -eq $python) {
    Write-Host "Python 3.10 or newer was not found."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Installing Python 3.12 with winget..."
        winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "Python installation failed. Please install Python manually and run this installer again."
        }
        $python = Find-Python
        if ($null -eq $python) {
            throw "Python appears to be installed, but this PowerShell session cannot find it yet. Open a new PowerShell window and run .\install_app.ps1 again."
        }
    } else {
        Write-Host ""
        Write-Host "winget was not found, so this installer cannot install Python automatically."
        Write-Host "Please install Python from https://www.python.org/downloads/ and run this installer again."
        Start-Process "https://www.python.org/downloads/"
        exit 1
    }
}

Write-Host "Using Python command: $($python.Display)"

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Host "Creating local virtual environment in .venv..."
    Invoke-Python -Python $python -PythonArgs @("-m", "venv", ".venv")
} else {
    Write-Host "Reusing existing .venv."
}

Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed."
}

Write-Host "Installing Pub Assist requirements..."
& $venvPython -m pip install -r requirements_app.txt
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed. Check the error above, then run .\install_app.ps1 again."
}

Write-Host ""
if (Get-Command node -ErrorAction SilentlyContinue) {
    Write-Host "Optional BibTeX Cleaner website-bundle route: Node.js found."
    if (Get-Command npx -ErrorAction SilentlyContinue) {
        Write-Host "Optional BibTeX Cleaner npm/npx route: npx found."
        Write-Host "  Pub Assist can run: npx --yes bibtex-tidy@latest"
    } else {
        Write-Host "Optional BibTeX Cleaner npm/npx route: npx was not found."
    }
} else {
    Write-Host "Optional BibTeX Cleaner engines: Node.js was not found."
    Write-Host "  Install Node.js LTS to use the website-bundle or npm/npx cleaner engines:"
    Write-Host "  winget install OpenJS.NodeJS.LTS"
}

Write-Host ""
Write-Host "Pub Assist is ready."
Write-Host "Launch it with .\start_app.ps1"
Write-Host ""
