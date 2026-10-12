param(
    [Parameter(Mandatory=$true)][string[]]$TemplatePath,
    [string]$AssemblyPath,
    [string]$ReportPath,
    [string]$RoundtripDirectory,
    [string]$QrImageDirectory
)
$ErrorActionPreference='Stop'
if($PSVersionTable.PSVersion.Major -ge 6){
    throw 'Use Windows PowerShell 5.1 powershell.exe, not pwsh, for these .NET Framework Kingdee libraries.'
}
if(-not $AssemblyPath){
    foreach($candidate in @(
        'C:\Program Files (x86)\Kingdee\K3Cloud\DeskClient\K3CloudClientX86\Kingdee.BOS.NotePrinting.dll',
        'C:\Program Files (x86)\Kingdee\K3Cloud\DeskClient\K3CloudClient\Kingdee.BOS.NotePrinting.dll'
    )){
        if(Test-Path -LiteralPath $candidate){$AssemblyPath=$candidate;break}
    }
}
if(-not $AssemblyPath -or -not (Test-Path -LiteralPath $AssemblyPath)){
    throw 'Matching Kingdee library unavailable; preserve candidate and report native check as not performed.'
}
$a=[Reflection.Assembly]::LoadFrom($AssemblyPath)
$prefix='Kingdee.BOS.NotePrinting.ReportOne'
$results=[Collections.ArrayList]::new()
foreach($path in $TemplatePath){
    try {
        $x=[xml][IO.File]::ReadAllText((Resolve-Path -LiteralPath $path).Path)
        $controls=$x.SelectNodes('/DocRoot/Report/Page/Sub-objects/*')
        foreach($node in $controls){
            if($node.Name -notin @('Text','Barcode','Currency')){
                throw ('Unsupported control registration: '+$node.Name+'. Extend native toolbox registration before claiming full validation.')
            }
        }
        $chain=[Collections.ArrayList]::new()
        foreach($pair in @(@('Text','ToolboxTextObject'),@('Barcode','ToolboxBarcode'),@('Currency','ToolboxCurrencyObject'))){
            $tb=[Activator]::CreateInstance($a.GetType($prefix+'.Common.GUI.'+$pair[1],$true))
            $tb.setKey($pair[0])
            [void]$chain.Add($tb)
        }
        $reader=[Activator]::CreateInstance($a.GetType($prefix+'.Print.Designer.Model.IO.R1PrintXmlReader',$true))
        $reader.SetXmlTransChain($chain)
        $dataTrans=[Activator]::CreateInstance($a.GetType($prefix+'.NoteDataXmlTrans',$true))
        $model=$reader.FromXml($x.DocumentElement,$dataTrans)
        foreach($node in $controls){
            if($null -eq $model.GetElementById($node.GetAttribute('id'))){
                throw ('Native reader lost control '+$node.GetAttribute('id'))
            }
        }
        $writer=[Activator]::CreateInstance($a.GetType($prefix+'.Print.Designer.Model.IO.R1PrintXmlWriter',$true))
        $writer.setXmlTransChain($chain)
        $roundtrip=$writer.toXml($model,$dataTrans)
        $rtNodes=$roundtrip.SelectNodes('Report/Page/Sub-objects/*')
        if($rtNodes.Count -ne $controls.Count){throw 'Native roundtrip changed control count.'}
        $rtMap=@{}
        foreach($node in $rtNodes){$rtMap[$node.GetAttribute('id')]=$node}
        foreach($node in $controls){
            $rt=$rtMap[$node.GetAttribute('id')]
            if(-not $rt -or $rt.Name -ne $node.Name){throw 'Roundtrip changed control ID or type.'}
            foreach($attribute in @('x','y','width','height')){
                if($rt.GetAttribute($attribute) -ne $node.GetAttribute($attribute)){
                    throw ('Roundtrip changed '+$attribute+' of '+$node.GetAttribute('id'))
                }
            }
            $d=$node.SelectSingleNode('Data')
            $rd=$rt.SelectSingleNode('Data')
            if($d -and $d.InnerText -ne $rd.InnerText){throw ('Roundtrip changed data content of '+$node.GetAttribute('id'))}
            if($d){
                foreach($attribute in @('dataSource','bindField','Type')){
                    if($d.GetAttribute($attribute) -ne $rd.GetAttribute($attribute)){
                        throw ('Roundtrip changed data binding of '+$node.GetAttribute('id'))
                    }
                }
            }
        }
        $qrResults=[Collections.ArrayList]::new()
        foreach($node in $controls){
            if($node.Name -eq 'Barcode' -and $node.GetAttribute('EncodeType') -eq 'Qrcode'){
                $d=$node.SelectSingleNode('Data')
                if($d -and -not $d.GetAttribute('bindField') -and $d.InnerText){
                    $type=$a.GetType($prefix+'.Print.Engine.Exporter.Impl.R1PBarcode_W2V',$true)
                    $method=$type.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance') |
                        Where-Object {$_.Name -eq 'loadImage' -and $_.GetParameters().Count -eq 4} |
                        Select-Object -First 1
                    if(-not $method){throw 'Native barcode loadImage signature unavailable.'}
                    $image=$method.Invoke($null,@($model.GetElementById($node.GetAttribute('id')),$d.InnerText,1,$false))
                    if($null -eq $image){throw 'Native static QR image generation returned null.'}
                    if($QrImageDirectory){
                        [IO.Directory]::CreateDirectory($QrImageDirectory)|Out-Null
                        $image.Save((Join-Path $QrImageDirectory ($node.GetAttribute('id')+'.png')))
                    }
                    [void]$qrResults.Add([pscustomobject]@{ID=$node.GetAttribute('id');Size=($image.Width.ToString()+'x'+$image.Height.ToString())})
                    $image.Dispose()
                }else{
                    [void]$qrResults.Add([pscustomobject]@{ID=$node.GetAttribute('id');Status='Dynamic value requires business preview'})
                }
            }
        }
        if($RoundtripDirectory){
            [IO.Directory]::CreateDirectory($RoundtripDirectory)|Out-Null
            [IO.File]::WriteAllText((Join-Path $RoundtripDirectory ([IO.Path]::GetFileName($path))),
                $roundtrip.OuterXml,[Text.UTF8Encoding]::new($false))
        }
        [void]$results.Add([pscustomobject]@{
            File=[IO.Path]::GetFileName($path);Passed=$true;SourceControls=$controls.Count;
            RoundtripControls=$rtNodes.Count;AllIDsFound=$true;GeometryAndDataPreserved=$true;
            StylesVersion=$x.DocRoot.Styles.version;QR=$qrResults.ToArray();
            Warning=$reader.GetWarning();AssemblyVersion=$a.GetName().Version.ToString()
        })
    }catch{
        [void]$results.Add([pscustomobject]@{File=[IO.Path]::GetFileName($path);Passed=$false;Error=$_.Exception.ToString()})
    }
}
$json=ConvertTo-Json -InputObject $results.ToArray() -Depth 8
Write-Output $json
if($ReportPath){
    $absolute=[IO.Path]::GetFullPath($ReportPath)
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($absolute))|Out-Null
    [IO.File]::WriteAllText($absolute,$json,[Text.UTF8Encoding]::new($false))
}
if(@($results|Where-Object{-not $_.Passed}).Count){exit 1}
exit 0
