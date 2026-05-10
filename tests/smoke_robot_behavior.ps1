$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$serverScript = Join-Path $root "services\webhook-receiver\server.py"
$analyzeScript = Join-Path $root "skills\robot-behavior\scripts\analyze_emotion.py"

$passed = 0
$total = 6
$caseResults = @()

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) { throw $Message }
}

function Run-Case {
    param([string]$Id, [string]$Name, [scriptblock]$Body)
    Write-Host ""
    Write-Host "[$Id] $Name"
    try {
        & $Body
        Write-Host "PASS"
        $script:passed += 1
        $script:caseResults += "$Id PASS"
    } catch {
        Write-Host "FAIL: $($_.Exception.Message)"
        $script:caseResults += "$Id FAIL"
    }
}

function Decode-UEscape {
    param([string]$Escaped)
    [Regex]::Unescape($Escaped)
}

function Make-Body {
    param([string]$EscapedText)
    $obj = @{ content = (Decode-UEscape $EscapedText) }
    $obj | ConvertTo-Json -Compress
}

function Invoke-JsonPost {
    param([string]$Url, [string]$Body)
    try {
        $resp = Invoke-WebRequest -UseBasicParsing -Method Post -Uri $Url -ContentType "application/json" -Body $Body
        [pscustomobject]@{
            Raw = $resp.Content
            Json = ($resp.Content | ConvertFrom-Json)
        }
    } catch {
        $raw = ""
        if ($_.Exception.Response -and $_.Exception.Response.GetResponseStream()) {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $raw = $reader.ReadToEnd()
            $reader.Close()
        }
        $json = $null
        try { $json = $raw | ConvertFrom-Json } catch {}
        [pscustomobject]@{ Raw = $raw; Json = $json }
    }
}

$env:EMOTION_PROVIDER = "mock"
$serverProc = Start-Process -FilePath python -ArgumentList $serverScript -PassThru -WindowStyle Hidden
Start-Sleep -Milliseconds 800

try {
    $ready = $false
    for ($i = 0; $i -lt 10; $i++) {
        try {
            $health = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/health
            if ($health.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
        Start-Sleep -Milliseconds 300
    }
    Assert-True $ready "server not ready on /health"

    Run-Case -Id "1" -Name "single-simple-emotion" -Body {
        $resp = Invoke-JsonPost -Url "http://127.0.0.1:8765/emotion" -Body (Make-Body "\u6211\u5f88\u5f00\u5fc3")
        Assert-True ($resp.Json -ne $null) ("not json: " + $resp.Raw)
        Assert-True ($resp.Json.action_sequence.Count -gt 0) ("empty action_sequence: " + $resp.Raw)
        Assert-True ($resp.Json.action_sequence[-1] -eq 0) ("tail not 0: " + $resp.Raw)
        foreach ($k in @("status","emotion","action_sequence","command_id","client_id")) {
            Assert-True ($null -ne $resp.Json.$k) ("missing field " + $k + " raw=" + $resp.Raw)
        }
    }

    Run-Case -Id "2" -Name "single-empty-content" -Body {
        $resp = Invoke-JsonPost -Url "http://127.0.0.1:8765/emotion" -Body (Make-Body "")
        Assert-True ($resp.Json -ne $null) ("not json: " + $resp.Raw)
        Assert-True ($resp.Json.status -ne "error") ("status is error: " + $resp.Raw)
        Assert-True ($resp.Json.action_sequence -ne $null) ("missing action_sequence: " + $resp.Raw)
        Assert-True ($resp.Json.action_sequence.Count -eq 1 -and $resp.Json.action_sequence[0] -eq 0) ("not [0]: " + $resp.Raw)
    }

    Run-Case -Id "3" -Name "multi-turning-point-story" -Body {
        $story = "\u5c0f\u660e\u8d70\u8fdb\u6559\u5ba4\uff0c\u8001\u5e08\u8868\u626c\u4e86\u4ed6\uff0c\u4ed6\u6fc0\u52a8\u5730\u8dd1\u53bb\u544a\u8bc9\u670b\u53cb"
        $resp = Invoke-JsonPost -Url "http://127.0.0.1:8765/emotion" -Body (Make-Body $story)
        Assert-True ($resp.Json -ne $null) ("not json: " + $resp.Raw)
        Assert-True ($resp.Json.action_sequence.Count -gt 2) ("action_sequence too short: " + $resp.Raw)
        $seq = @($resp.Json.action_sequence)
        for ($i = 0; $i -lt $seq.Count - 1; $i++) {
            Assert-True (-not ($seq[$i] -eq 0 -and $seq[$i + 1] -eq 0)) ("adjacent zeros: " + $resp.Raw)
        }

        $anRaw = python $analyzeScript --provider mock --input (Decode-UEscape $story)
        $anJson = $anRaw | ConvertFrom-Json
        Assert-True ($null -ne $anJson.segments) ("analyze_emotion missing segments: " + $anRaw)
        Assert-True ($anJson.segments.Count -ge 2) ("segments less than 2: " + $anRaw)
    }

    Run-Case -Id "4" -Name "multi-emotion-reversal" -Body {
        $story = "\u5979\u6ee1\u6000\u671f\u5f85\u5730\u6253\u5f00\u4fe1\u5c01\uff0c\u5374\u53d1\u73b0\u81ea\u5df1\u843d\u699c\u4e86\uff0c\u9ed8\u9ed8\u79bb\u5f00\u4e86\u8003\u573a"
        $resp = Invoke-JsonPost -Url "http://127.0.0.1:8765/emotion" -Body (Make-Body $story)
        Assert-True ($resp.Json -ne $null) ("not json: " + $resp.Raw)
        $seq = @($resp.Json.action_sequence)
        Assert-True ($seq.Count -gt 0) ("empty action_sequence: " + $resp.Raw)
        Assert-True ($seq[-1] -eq 0) ("tail not 0: " + $resp.Raw)
        for ($i = 0; $i -lt $seq.Count - 1; $i++) {
            Assert-True ($seq[$i] -ne 0) ("zero in middle: " + $resp.Raw)
        }
    }

    Run-Case -Id "5" -Name "emotion-field-compat" -Body {
        $resp = Invoke-JsonPost -Url "http://127.0.0.1:8765/emotion" -Body (Make-Body "\u6211\u5f88\u5f00\u5fc3")
        Assert-True ($resp.Json -ne $null) ("not json: " + $resp.Raw)
        $actual = @($resp.Json.PSObject.Properties.Name) | Sort-Object
        $expected = @("status","emotion","action_sequence","command_id","client_id") | Sort-Object
        Assert-True (($actual -join ",") -eq ($expected -join ",")) ("field mismatch actual=" + ($actual -join ",") + " raw=" + $resp.Raw)
        Assert-True ($null -eq $resp.Json.segments) ("segments should not be exposed: " + $resp.Raw)
    }

    Run-Case -Id "6" -Name "poll-ack-e2e" -Body {
        $create = Invoke-JsonPost -Url "http://127.0.0.1:8765/emotion" -Body (Make-Body "\u6211\u5f88\u5f00\u5fc3")
        Assert-True ($create.Json -ne $null) ("create action failed: " + $create.Raw)

        $poll1Raw = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/poll/milk_duos_001
        $poll1 = $poll1Raw.Content | ConvertFrom-Json
        Assert-True ($null -ne $poll1.command_id) ("missing command_id: " + $poll1Raw.Content)

        $ackBody = ('{"command_id":"' + $poll1.command_id + '"}')
        $ack = Invoke-JsonPost -Url "http://127.0.0.1:8765/ack/milk_duos_001" -Body $ackBody
        Assert-True ($ack.Json.status -eq "success") ("ack failed: " + $ack.Raw)

        $poll2Raw = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/poll/milk_duos_001
        $poll2 = $poll2Raw.Content | ConvertFrom-Json
        Assert-True ($poll2.status -eq "no_action") ("poll after ack not no_action: " + $poll2Raw.Content)
    }
}
finally {
    if ($serverProc -and -not $serverProc.HasExited) {
        Stop-Process -Id $serverProc.Id -Force
    }
}

Write-Host ""
Write-Host ("Summary: " + $passed + "/" + $total + " passed")
foreach ($line in $caseResults) { Write-Host $line }
