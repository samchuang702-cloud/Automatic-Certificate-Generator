param(
    [Parameter(Mandatory = $true)]
    [string]$TemplatePath,

    [Parameter(Mandatory = $true)]
    [string]$WorkingDocPath,

    [Parameter(Mandatory = $true)]
    [string]$DataPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

function Get-DataValue {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Data,

        [Parameter(Mandatory = $true)]
        [string]$Key
    )

    $property = $Data.PSObject.Properties[$Key]
    if ($null -eq $property -or $null -eq $property.Value) {
        return $null
    }

    return [string]$property.Value
}

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

    foreach ($section in @($Document.Sections)) {
        foreach ($header in @($section.Headers)) {
            Replace-InRange -Range $header.Range -FindText $FindText -ReplaceText $ReplaceText
        }
        foreach ($footer in @($section.Footers)) {
            Replace-InRange -Range $footer.Range -FindText $FindText -ReplaceText $ReplaceText
        }
    }

    foreach ($shape in @($Document.Shapes)) {
        if ($shape.TextFrame.HasText -eq -1) {
            Replace-InRange -Range $shape.TextFrame.TextRange -FindText $FindText -ReplaceText $ReplaceText
        }
    }
}

$word = $null
$document = $null

try {
    Copy-Item -LiteralPath $TemplatePath -Destination $WorkingDocPath -Force

    $data = Get-Content -LiteralPath $DataPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $document = $word.Documents.Open($WorkingDocPath)

    $fields = @($document.Fields)
    foreach ($field in $fields) {
        $code = [string]$field.Code.Text
        if ($code -match 'MERGEFIELD\s+"?([^"\s]+)"?') {
            $fieldName = $matches[1].Trim()
            $fieldValue = Get-DataValue -Data $data -Key $fieldName
            if ($null -ne $fieldValue) {
                $field.Result.Text = $fieldValue
                $field.Unlink() | Out-Null
            }
        }
    }

    foreach ($replacement in @($data.word_replacements)) {
        if ($null -ne $replacement.old -and $null -ne $replacement.new) {
            Replace-InDocument -Document $document -FindText ([string]$replacement.old) -ReplaceText ([string]$replacement.new)
        }
    }

    # 17 is wdExportFormatPDF.
    $document.ExportAsFixedFormat($OutputPath, 17)
}
finally {
    if ($null -ne $document) {
        $document.Close($false) | Out-Null
    }

    if ($null -ne $word) {
        $word.Quit() | Out-Null
    }
}
