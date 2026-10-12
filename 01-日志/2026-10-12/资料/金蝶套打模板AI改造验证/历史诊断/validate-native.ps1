param([string[]]$Paths)
$ErrorActionPreference='Stop'
$a=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Kingdee\K3Cloud\DeskClient\K3CloudClientX86\Kingdee.BOS.NotePrinting.dll')
foreach($path in $Paths) {
try {
$chain=[Collections.ArrayList]::new()
foreach($pair in @(@('Text','ToolboxTextObject'),@('Barcode','ToolboxBarcode'),@('Currency','ToolboxCurrencyObject'))) { $tb=[Activator]::CreateInstance($a.GetType('Kingdee.BOS.NotePrinting.ReportOne.Common.GUI.'+$pair[1])); $tb.setKey($pair[0]); [void]$chain.Add($tb) }
$r=[Activator]::CreateInstance($a.GetType('Kingdee.BOS.NotePrinting.ReportOne.Print.Designer.Model.IO.R1PrintXmlReader'))
$r.SetXmlTransChain($chain)
$dt=[Activator]::CreateInstance($a.GetType('Kingdee.BOS.NotePrinting.ReportOne.NoteDataXmlTrans'))
$x=[xml][IO.File]::ReadAllText($path)
$m=$r.FromXml($x.DocumentElement,$dt)
$w=[Activator]::CreateInstance($a.GetType('Kingdee.BOS.NotePrinting.ReportOne.Print.Designer.Model.IO.R1PrintXmlWriter'))
$w.setXmlTransChain($chain)
$o=$w.toXml($m,$dt)
[pscustomobject]@{Path=$path;Passed=$true;SourceControls=$x.SelectNodes('/DocRoot/Report/Page/Sub-objects/*').Count;RoundtripControls=$o.SelectNodes('Report/Page/Sub-objects/*').Count;Warning=$r.GetWarning()} | ConvertTo-Json -Compress
[IO.File]::WriteAllText((Join-Path $PSScriptRoot ('native-roundtrip-'+[IO.Path]::GetFileName($path))),$o.OuterXml,[Text.UTF8Encoding]::new($false))
}catch{[pscustomobject]@{Path=$path;Passed=$false;Error=$_.Exception.ToString()} | ConvertTo-Json -Compress}
}