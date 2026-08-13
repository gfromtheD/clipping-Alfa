[CmdletBinding()]
param(
    [string]$Language = "auto",
    [string]$InputVideo,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$AdditionalArguments
)

$projectRoot = $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$entrypoint = Join-Path $projectRoot "scripts\process_video.py"

if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe el intérprete esperado del entorno virtual: $python"
}

$arguments = @($entrypoint, "--language", $Language)
if ($InputVideo) {
    $arguments += @("--input", $InputVideo)
}
if ($AdditionalArguments) {
    $arguments += $AdditionalArguments
}

& $python @arguments
exit $LASTEXITCODE
