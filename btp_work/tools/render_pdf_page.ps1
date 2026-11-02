param([Parameter(Mandatory=$true)][string]$Pdf,[Parameter(Mandatory=$true)][int]$Page,[Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.DataReader,Windows.Storage.Streams,ContentType=WindowsRuntime]
function Await-Operation($Operation,[Type]$ResultType) {
    $method=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetGenericArguments().Count -eq 1 } | Select-Object -First 1
    $task=$method.MakeGenericMethod($ResultType).Invoke($null,@($Operation))
    $task.Wait()
    return $task.Result
}
function Await-Action($Operation) {
    $method=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
    $task=$method.Invoke($null,@($Operation))
    $task.Wait()
}
$root=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$target=[IO.Path]::GetFullPath($Out)
if (-not $target.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be under btp_work' }
if (Test-Path -LiteralPath $target) { throw 'Output already exists' }
$source=Await-Operation ([Windows.Storage.StorageFile]::GetFileFromPathAsync([IO.Path]::GetFullPath($Pdf))) ([Windows.Storage.StorageFile])
$document=Await-Operation ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($source)) ([Windows.Data.Pdf.PdfDocument])
$pdfPage=$document.GetPage($Page-1)
$stream=New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
$options=New-Object Windows.Data.Pdf.PdfPageRenderOptions
$options.DestinationWidth=2200
Await-Action ($pdfPage.RenderToStreamAsync($stream,$options))
$reader=New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
$null=Await-Operation ($reader.LoadAsync([uint32]$stream.Size)) ([uint32])
$bytes=New-Object byte[] ([int]$stream.Size)
$reader.ReadBytes($bytes)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target)) | Out-Null
[IO.File]::WriteAllBytes($target,$bytes)
$reader.Dispose();$stream.Dispose();$pdfPage.Dispose()
[pscustomobject]@{source=$Pdf;page=$Page;output=$target;bytes=$bytes.Length}|ConvertTo-Json
