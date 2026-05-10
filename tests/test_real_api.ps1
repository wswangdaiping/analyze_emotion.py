$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$analyzeScript = Join-Path $root "skills\robot-behavior\scripts\analyze_emotion.py"

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Decode-UEscape {
    param([string]$Escaped)
    [Regex]::Unescape($Escaped)
}

function Run-Case {
    param(
        [string]$Id,
        [string]$Name,
        [string]$InputTextEscaped,
        [scriptblock]$Validator
    )
    Write-Host ""
    Write-Host "[$Id] $Name"
    $inputText = Decode-UEscape $InputTextEscaped
    $tmpFile = Join-Path $PSScriptRoot ("tmp_input_" + $Id + ".json")
    $jsonObj = @{ content = $inputText }
    $jsonText = $jsonObj | ConvertTo-Json -Compress
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tmpFile, $jsonText, $utf8NoBom)
    $raw = python $analyzeScript --provider dashscope --input-file $tmpFile --pretty
    Write-Host "Raw Response:"
    Write-Host $raw
    try {
        $json = $raw | ConvertFrom-Json
        & $Validator $json
        Write-Host "PASS"
    } catch {
        Write-Host "FAIL: $($_.Exception.Message)"
    } finally {
        if (Test-Path $tmpFile) {
            Remove-Item -LiteralPath $tmpFile -Force
        }
    }
}

if (-not $env:DASHSCOPE_API_KEY) {
    throw "DASHSCOPE_API_KEY not found in environment."
}

$env:EMOTION_PROVIDER = "dashscope"

Run-Case -Id "A" -Name "single simple emotion" -InputTextEscaped "\u6211\u5f88\u5f00\u5fc3" -Validator {
    param($json)
    Assert-True ($json.status -eq "success") ("status not success: " + ($json | ConvertTo-Json -Compress))
    Assert-True ($json.action_sequence.Count -ge 2) ("action_sequence length < 2")
    Assert-True ($json.action_sequence[-1] -eq 0) ("tail not 0")
}

Run-Case -Id "B" -Name "multi turning-point story" -InputTextEscaped "\u5c0f\u660e\u8d70\u8fdb\u6559\u5ba4\uff0c\u8001\u5e08\u8868\u626c\u4e86\u4ed6\uff0c\u4ed6\u6fc0\u52a8\u5730\u8dd1\u53bb\u544a\u8bc9\u670b\u53cb" -Validator {
    param($json)
    Assert-True ($json.status -eq "success") ("status not success: " + ($json | ConvertTo-Json -Compress))
    Assert-True ($null -ne $json.segments) "segments missing"
    Assert-True ($json.segments.Count -ge 2) ("segments < 2")
    $seq = @($json.action_sequence)
    for ($i = 0; $i -lt $seq.Count - 1; $i++) {
        Assert-True (-not ($seq[$i] -eq 0 -and $seq[$i + 1] -eq 0)) ("adjacent zeros in sequence")
    }
    Assert-True ($seq[-1] -eq 0) ("tail not 0")
}

Run-Case -Id "C" -Name "emotion reversal story" -InputTextEscaped "\u5979\u6ee1\u6000\u671f\u5f85\u5730\u6253\u5f00\u4fe1\u5c01\uff0c\u5374\u53d1\u73b0\u81ea\u5df1\u843d\u699c\u4e86\uff0c\u9ed8\u9ed8\u79bb\u5f00\u4e86\u8003\u573a" -Validator {
    param($json)
    Assert-True ($json.status -eq "success") ("status not success: " + ($json | ConvertTo-Json -Compress))
    $seq = @($json.action_sequence)
    Assert-True ($seq.Count -gt 0) ("empty action_sequence")
    Assert-True ($seq[-1] -eq 0) ("tail not 0")
}
