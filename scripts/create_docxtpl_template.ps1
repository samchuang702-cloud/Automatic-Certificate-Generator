param(
    [Parameter(Mandatory = $true)]
    [string]$SourceDocPath,

    [Parameter(Mandatory = $true)]
    [string]$TemplateDocxPath,

    [Parameter(Mandatory = $true)]
    [string]$ReplacementsPath
)

$ErrorActionPreference = "Stop"

function Replace-InRange {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Range,

        [Parameter(Mandatory = $true)]
        [string]$FindText,

        [Parameter(Mandatory = $true)]
        [string]$ReplaceText
    )

    if ([string]::IsNullOrEmpty($FindText)) {
        return
    }

    $find = $Range.Find
    $find.ClearFormatting() | Out-Null
    $find.Replacement.ClearFormatting() | Out-Null
    $find.Execute(
        $FindText,
        $false,
        $false,
        $false,
        $false,
        $false,
        $true,
        1,
        $false,
        $ReplaceText,
        2
    ) | Out-Null
}

function Replace-InDocument {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Document,

        [Parameter(Mandatory = $true)]
        [string]$FindText,

        [Parameter(Mandatory = $true)]
        [string]$ReplaceText
    )

    Replace-InRange -Range $Document.Content -FindText $FindText -ReplaceText $ReplaceText
}

$word = $null
$document = $null

try {
    $replacements = Get-Content -LiteralPath $ReplacementsPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3

    if (Test-Path -LiteralPath $TemplateDocxPath) {
        Remove-Item -LiteralPath $TemplateDocxPath -Force
    }

    $document = $word.Documents.Open(
        $SourceDocPath,
        $false,
        $false,
        $false,
        "",
        "",
        $false,
        "",
        "",
        0,
        0,
        $false,
        $true,
        0,
        $true
    )

    foreach ($replacement in @($replacements)) {
        Replace-InDocument -Document $document -FindText ([string]$replacement.old) -ReplaceText ([string]$replacement.new)
    }

    # 12 is wdFormatXMLDocument (.docx).
    $document.SaveAs2($TemplateDocxPath, 12)
}
finally {
    if ($null -ne $document) {
        $document.Close($false) | Out-Null
    }

    if ($null -ne $word) {
        $word.Quit() | Out-Null
    }
}
