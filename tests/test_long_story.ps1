$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = Split-Path -Parent $PSScriptRoot
$analyzeScript = Join-Path $root "skills\robot-behavior\scripts\analyze_emotion.py"
$tmpFile = Join-Path $PSScriptRoot "tmp_input.json"
$reportFile = Join-Path $PSScriptRoot "long_story_report.md"

function U {
    param([string]$Escaped)
    [Regex]::Unescape($Escaped)
}

$L = @{
    Title = (U '\u957f\u6545\u4e8b\u89e3\u6790\u6d4b\u8bd5')
    CurrentTime = (U '\u5f53\u524d\u65f6\u95f4')
    InputStory = (U '\u8f93\u5165\u6545\u4e8b\u539f\u6587')
    SegmentUnit = (U '\u6bb5')
    ActionLength = (U '\u52a8\u4f5c\u5e8f\u5217\u957f\u5ea6')
    Summary = (U '\u6c47\u603b\u8868\u683c')
    ReportSaved = (U '\u5b8c\u6574 Markdown \u62a5\u544a\u5df2\u4fdd\u5b58\u5230')
    Scene = (U '\u573a\u666f')
    SegmentCount = (U '\u5206\u6bb5\u6570')
    ActionCount = (U '\u52a8\u4f5c\u6570')
    ActionSequence = (U '\u52a8\u4f5c\u5e8f\u5217')
    GeneratedAt = (U '\u751f\u6210\u65f6\u95f4')
    Story = (U '\u8f93\u5165\u6545\u4e8b')
    Action = (U '\u52a8\u4f5c')
}

$cases = @(
    [pscustomobject]@{
        Id = "1"
        Scene = (U '\u5355\u4e00\u60c5\u7eea\u957f\u6545\u4e8b\uff08\u5f00\u5fc3\uff09')
        Story = (U '\u5c0f\u660e\u4eca\u5929\u6536\u5230\u4e86\u5927\u5b66\u5f55\u53d6\u901a\u77e5\u4e66\uff0c\u4ed6\u6fc0\u52a8\u5730\u51b2\u51fa\u623f\u95f4\u544a\u8bc9\u5988\u5988\uff0c\u5988\u5988\u542c\u5b8c\u6cea\u6d41\u6ee1\u9762\u5730\u62b1\u4f4f\u4ed6\uff0c\u4e24\u4e2a\u4eba\u5728\u5ba2\u5385\u91cc\u7b11\u7740\u54ed\u7740\uff0c\u90bb\u5c45\u542c\u5230\u52a8\u9759\u4e5f\u6765\u9053\u559c\u3002')
    },
    [pscustomobject]@{
        Id = "2"
        Scene = (U '\u60c5\u7eea\u53cd\u8f6c\u6545\u4e8b\uff08\u7531\u60b2\u8f6c\u559c\uff09')
        Story = (U '\u5c0f\u7ea2\u6ee1\u6000\u671f\u5f85\u5730\u6253\u5f00\u6210\u7ee9\u5355\uff0c\u5374\u53d1\u73b0\u81ea\u5df1\u4e0d\u53ca\u683c\uff0c\u5979\u4e00\u4e2a\u4eba\u5750\u5728\u8d70\u5eca\u53d1\u5446\u3002\u73ed\u4e3b\u4efb\u8def\u8fc7\u770b\u5230\u5979\uff0c\u628a\u5979\u53eb\u8fdb\u529e\u516c\u5ba4\uff0c\u544a\u8bc9\u5979\u5176\u5b9e\u8001\u5e08\u6539\u9519\u4e86\uff0c\u5979\u5176\u5b9e\u662f\u6ee1\u5206\u3002')
    },
    [pscustomobject]@{
        Id = "3"
        Scene = (U '\u591a\u60c5\u7eea\u8f6c\u6298\u6545\u4e8b\uff08\u7d27\u5f20\u2192\u5bb3\u6015\u2192\u91ca\u7136\uff09')
        Story = (U '\u6df1\u591c\u5c0f\u5df7\u91cc\uff0c\u5c0f\u674e\u542c\u5230\u8eab\u540e\u6709\u811a\u6b65\u58f0\uff0c\u4ed6\u52a0\u5feb\u6b65\u4f10\uff0c\u811a\u6b65\u58f0\u4e5f\u8ddf\u7740\u52a0\u5feb\u3002\u4ed6\u731b\u5730\u56de\u5934\uff0c\u53d1\u73b0\u662f\u4e00\u53ea\u6d41\u6d6a\u732b\u8ddf\u7740\u4ed6\u3002\u4ed6\u8e72\u4e0b\u6765\u6478\u4e86\u6478\u732b\uff0c\u7b11\u7740\u7ee7\u7eed\u8d70\u56de\u5bb6\u3002')
    },
    [pscustomobject]@{
        Id = "4"
        Scene = (U '\u53d9\u4e8b\u5f27\u7ebf\u5b8c\u6574\u7684\u6545\u4e8b\uff08\u51fa\u53d1\u2192\u53d7\u632b\u2192\u575a\u6301\u2192\u6210\u529f\uff09')
        Story = (U '\u5c0f\u534e\u7b2c\u4e00\u6b21\u53c2\u52a0\u9a6c\u62c9\u677e\u6bd4\u8d5b\uff0c\u51fa\u53d1\u65f6\u610f\u6c14\u98ce\u53d1\u5730\u51b2\u5728\u524d\u9762\u3002\u8dd1\u5230\u4e00\u534a\u4ed6\u4f53\u529b\u4e0d\u652f\uff0c\u817f\u5f00\u59cb\u62bd\u7b4b\uff0c\u51e0\u4e4e\u60f3\u8981\u653e\u5f03\u3002\u65c1\u8fb9\u7684\u964c\u751f\u4eba\u62cd\u4e86\u62cd\u4ed6\u7684\u80a9\u8180\u8bf4\u52a0\u6cb9\u3002\u4ed6\u54ac\u7259\u575a\u6301\u8dd1\u5b8c\u4e86\u5168\u7a0b\uff0c\u51b2\u8fc7\u7ec8\u70b9\u7ebf\u7684\u90a3\u4e00\u523b\u4ed6\u4e3e\u8d77\u53cc\u624b\u5927\u558a\u3002')
    },
    [pscustomobject]@{
        Id = "5"
        Scene = (U '\u5e73\u6de1\u65e5\u5e38\u6545\u4e8b\uff08\u65e0\u660e\u663e\u60c5\u7eea\u9ad8\u6f6e\uff09')
        Story = (U '\u65e9\u4e0a\u4e03\u70b9\u95f9\u949f\u54cd\u4e86\uff0c\u5c0f\u660e\u5173\u6389\u95f9\u949f\u7ffb\u4e86\u4e2a\u8eab\u3002\u4ed6\u6162\u6162\u722c\u8d77\u6765\u6d17\u8138\u5237\u7259\uff0c\u4e0b\u697c\u5403\u4e86\u7897\u7ca5\u3002\u51fa\u95e8\u65f6\u53d1\u73b0\u4e0b\u96e8\u4e86\uff0c\u4ed6\u56de\u53bb\u62ff\u4e86\u628a\u4f1e\uff0c\u7136\u540e\u9a91\u8f66\u53bb\u4e86\u516c\u53f8\u3002')
    },
    [pscustomobject]@{
        Id = "6"
        Scene = (U '\u9ad8\u6f6e\u5bc6\u96c6\u6545\u4e8b\uff08\u591a\u4e2a\u5f3a\u60c5\u7eea\u8282\u70b9\uff09')
        Story = (U '\u6bd4\u8d5b\u6700\u540e\u4e00\u79d2\uff0c\u5c0f\u5f3a\u63a5\u5230\u961f\u53cb\u4f20\u7403\uff0c\u4ed6\u8f6c\u8eab\u6295\u7bee\u3002\u7403\u5728\u7bee\u7b50\u8fb9\u7f18\u8f6c\u4e86\u4e00\u5708\uff0c\u6389\u4e86\u8fdb\u53bb\u3002\u5168\u573a\u6cb8\u817e\uff0c\u961f\u53cb\u4eec\u51b2\u8fc7\u6765\u628a\u4ed6\u62b1\u8d77\u6765\u3002\u9881\u5956\u53f0\u4e0a\u4ed6\u4e3e\u8d77\u5956\u676f\uff0c\u6cea\u6c34\u6a21\u7cca\u4e86\u89c6\u7ebf\u3002')
    }
)

function Format-ActionSequence {
    param($Sequence)

    if ($null -eq $Sequence) {
        return "[]"
    }

    $items = @($Sequence) | ForEach-Object { [string]$_ }
    return "[" + ($items -join ", ") + "]"
}

function Escape-MarkdownCell {
    param([string]$Text)

    if ($null -eq $Text) {
        return ""
    }

    return $Text.Replace('\', '\\').Replace('|', '\|').Replace("`r`n", "<br>").Replace("`n", "<br>")
}

function Get-DisplayWidth {
    param([string]$Text)

    if ($null -eq $Text) {
        return 0
    }

    $width = 0
    foreach ($ch in $Text.ToCharArray()) {
        if ([int][char]$ch -gt 127) {
            $width += 2
        } else {
            $width += 1
        }
    }
    return $width
}

function Pad-DisplayRight {
    param(
        [string]$Text,
        [int]$Width
    )

    $value = if ($null -eq $Text) { "" } else { $Text }
    $padding = [Math]::Max(0, $Width - (Get-DisplayWidth $value))
    return $value + (" " * $padding)
}

function Write-SummaryTable {
    param([array]$Results)

    $headers = @("Case", $L.Scene, $L.SegmentCount, $L.ActionCount, $L.ActionSequence)
    $rows = foreach ($result in $Results) {
        @(
            "Case $($result.Id)",
            $result.Scene,
            [string]$result.SegmentCount,
            [string]$result.ActionCount,
            $result.ActionSequenceText
        )
    }

    $widths = @()
    for ($i = 0; $i -lt $headers.Count; $i++) {
        $max = Get-DisplayWidth $headers[$i]
        foreach ($row in $rows) {
            $displayWidth = Get-DisplayWidth $row[$i]
            if ($displayWidth -gt $max) {
                $max = $displayWidth
            }
        }
        $widths += $max
    }

    $headerCells = for ($i = 0; $i -lt $headers.Count; $i++) {
        Pad-DisplayRight $headers[$i] $widths[$i]
    }
    Write-Host ($headerCells -join " | ")
    Write-Host (($widths | ForEach-Object { "-" * $_ }) -join "-+-")

    foreach ($row in $rows) {
        $cells = for ($i = 0; $i -lt $row.Count; $i++) {
            Pad-DisplayRight $row[$i] $widths[$i]
        }
        Write-Host ($cells -join " | ")
    }
}

function Write-MarkdownReport {
    param(
        [array]$Results,
        [string]$Path
    )

    $lines = @(
        "# $($L.Title)",
        "",
        "- $($L.GeneratedAt): $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
        "- Provider: dashscope",
        "",
        "| Case | $($L.Scene) | $($L.Story) | Segments | emotion_detected | $($L.ActionCount) | action_sequence |",
        "| --- | --- | --- | --- | --- | ---: | --- |"
    )

    foreach ($result in $Results) {
        $segmentText = if ($result.Segments.Count -gt 0) {
            (($result.Segments | ForEach-Object { "$($_.Index). $($_.Text) $($L.Action): $($_.ActionsText)" }) -join "<br>")
        } else {
            ""
        }

        $lines += "| Case $($result.Id) | $(Escape-MarkdownCell $result.Scene) | $(Escape-MarkdownCell $result.Story) | $(Escape-MarkdownCell $segmentText) | $(Escape-MarkdownCell $result.EmotionDetected) | $($result.ActionCount) | $(Escape-MarkdownCell $result.ActionSequenceText) |"
    }

    [System.IO.File]::WriteAllText($Path, ($lines -join [Environment]::NewLine), [System.Text.Encoding]::UTF8)
}

Write-Host "=== $($L.Title) ==="
Write-Host ("$($L.CurrentTime): " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))

if (-not (Test-Path $analyzeScript)) {
    throw "analyze_emotion.py not found: $analyzeScript"
}

$results = @()

try {
    foreach ($case in $cases) {
        Write-Host ""
        Write-Host "Case $($case.Id): $($case.Scene)"
        Write-Host "$($L.InputStory):"
        Write-Host $case.Story

        $inputJson = @{ content = $case.Story } | ConvertTo-Json -Compress
        [System.IO.File]::WriteAllText($tmpFile, $inputJson, [System.Text.Encoding]::UTF8)

        $stderrFile = Join-Path $PSScriptRoot "tmp_analyze_stderr.txt"
        $raw = & python $analyzeScript --input-file $tmpFile --provider dashscope 2>$stderrFile
        $exitCode = $LASTEXITCODE
        $stderr = if (Test-Path $stderrFile) { Get-Content -Raw -Path $stderrFile } else { "" }
        if (Test-Path $stderrFile) {
            Remove-Item -LiteralPath $stderrFile -Force
        }

        if ($exitCode -ne 0) {
            throw "Case $($case.Id) failed with exit code $exitCode. stderr: $stderr stdout: $raw"
        }

        $json = $raw | ConvertFrom-Json
        if ($json.status -ne "success") {
            throw "Case $($case.Id) returned non-success status: $raw"
        }

        $segments = @($json.segments)
        $actionSequence = @($json.action_sequence)
        $actionSequenceText = Format-ActionSequence $actionSequence
        $emotionDetected = [string]$json.emotion_detected

        Write-Host "segments ($($segments.Count) $($L.SegmentUnit)):"
        for ($i = 0; $i -lt $segments.Count; $i++) {
            $segment = $segments[$i]
            $segmentActions = Format-ActionSequence @($segment.actions)
            Write-Host ("  {0}. {1}" -f ($i + 1), $segment.text)
            Write-Host ("     actions: {0}" -f $segmentActions)
        }

        Write-Host "action_sequence:"
        Write-Host ("  " + $actionSequenceText)
        Write-Host ("emotion_detected: " + $emotionDetected)
        Write-Host ("$($L.ActionLength): " + $actionSequence.Count)
        Write-Host ("-" * 72)

        $reportSegments = for ($i = 0; $i -lt $segments.Count; $i++) {
            [pscustomobject]@{
                Index = $i + 1
                Text = [string]$segments[$i].text
                ActionsText = Format-ActionSequence @($segments[$i].actions)
            }
        }

        $results += [pscustomobject]@{
            Id = $case.Id
            Scene = $case.Scene
            Story = $case.Story
            SegmentCount = $segments.Count
            ActionCount = $actionSequence.Count
            ActionSequenceText = $actionSequenceText
            EmotionDetected = $emotionDetected
            Segments = @($reportSegments)
        }

        if ($case.Id -ne $cases[-1].Id) {
            Start-Sleep -Seconds 3
        }
    }
}
finally {
    if (Test-Path $tmpFile) {
        Remove-Item -LiteralPath $tmpFile -Force
    }
}

Write-Host ""
Write-Host "$($L.Summary):"
Write-SummaryTable -Results $results

Write-MarkdownReport -Results $results -Path $reportFile
Write-Host ""
Write-Host ("$($L.ReportSaved): " + $reportFile)
