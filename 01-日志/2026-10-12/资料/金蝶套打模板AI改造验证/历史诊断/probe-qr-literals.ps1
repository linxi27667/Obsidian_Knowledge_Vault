$a=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Kingdee\K3Cloud\DeskClient\K3CloudClientX86\Kingdee.BOS.NotePrinting.dll')
$gt=$a.GetType('Kingdee.BOS.NotePrinting.ReportOne.Print.Engine.Exporter.Impl.R1PBarcode_W2V')
foreach($m in ($gt.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance')|Where-Object{$_.Name -match 'loadImage|QRCode|CreateBarcode|GetBarcodeParameter'})) {
$m.ToString()
$body=$m.GetMethodBody(); if($body){$il=$body.GetILAsByteArray(); for($i=0;$i -lt $il.Length-4;$i++){if($il[$i]-eq 0x72){try{$token=[BitConverter]::ToInt32($il,$i+1); if(($token -band 0xff000000)-eq 0x70000000){'LITERAL '+$m.Module.ResolveString($token)}}catch{}}}}
}
$qr=$gt.GetMethod('CreatQRCodeImage',[Reflection.BindingFlags]'Public,NonPublic,Static')
try{$img=$qr.Invoke($null,@('OP093762')); 'QRCODE_IMAGE '+$img.Size.ToString(); $img.Save((Join-Path $PSScriptRoot 'qr-demo.png')); $img.Dispose()}catch{$_.Exception.GetBaseException().Message}