param(
    [Parameter(Mandatory = $true)]
    [string]$DocxPath,

    [Parameter(Mandatory = $true)]
    [string]$PdfPath
)

$ErrorActionPreference = "Stop"

$word = $null
$document = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $document = $word.Documents.Open($DocxPath)

    # 17 is wdExportFormatPDF.
    $document.ExportAsFixedFormat($PdfPath, 17)
}
finally {
    if ($null -ne $document) {
        $document.Close($false) | Out-Null
    }

    if ($null -ne $word) {
        $word.Quit() | Out-Null
    }
}
