$ErrorActionPreference='Stop'
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
public static class ILProbe {
 static Dictionary<short,OpCode> ops=new Dictionary<short,OpCode>();
 static ILProbe(){foreach(var f in typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static)){var v=(OpCode)f.GetValue(null);ops[v.Value]=v;}}
 public static void Show(MethodInfo m){
 Console.WriteLine("METHOD "+m.DeclaringType.FullName+"."+m.ToString());
 var b=m.GetMethodBody();if(b==null)return;var v=b.GetILAsByteArray();int p=0;
 while(p<v.Length){int start=p;short o=v[p++];if(o==0xfe)o=(short)(0xfe00|v[p++]);OpCode op;if(!ops.TryGetValue(o,out op))break;string val="";int count=0;
 switch(op.OperandType){
 case OperandType.InlineNone:break;
 case OperandType.ShortInlineI:case OperandType.ShortInlineBrTarget:case OperandType.ShortInlineVar:count=1;val=v[p].ToString();break;
 case OperandType.InlineVar:count=2;break;
 case OperandType.InlineI8:case OperandType.InlineR:count=8;break;
 case OperandType.InlineSwitch:count=4+4*BitConverter.ToInt32(v,p);break;
 default:count=4;int token=BitConverter.ToInt32(v,p);try{
 if(op.OperandType==OperandType.InlineString)val="STRING "+m.Module.ResolveString(token);
 else if(op.OperandType==OperandType.InlineMethod)val=m.Module.ResolveMethod(token).ToString();
 else if(op.OperandType==OperandType.InlineField)val=m.Module.ResolveField(token).ToString();
 else if(op.OperandType==OperandType.InlineType)val=m.Module.ResolveType(token).FullName;
 else val=token.ToString();}catch{val=token.ToString();}break;}
 if(op.OperandType==OperandType.InlineString||op.OperandType==OperandType.InlineMethod||op.OperandType==OperandType.InlineField)Console.WriteLine(start.ToString("X4")+" "+op.Name+" "+val);
 p+=count;
 }
 }
}
"@
$a=[Reflection.Assembly]::LoadFrom('C:\Program Files (x86)\Kingdee\K3Cloud\DeskClient\K3CloudClientX86\Kingdee.BOS.NotePrinting.dll')
foreach($q in @(
@('Kingdee.BOS.NotePrinting.ReportOne.Common.Model.IO.AbstractR1XmlReader','ParseObject'),
@('Kingdee.BOS.NotePrinting.ReportOne.Print.Designer.Model.IO.R1PrintXmlReader','LoadContainer'),
@('Kingdee.BOS.NotePrinting.ReportOne.Print.Designer.Model.XmlTrans.AbstractR1PrintXmlTrans','fromXml'),
@('Kingdee.BOS.NotePrinting.ReportOne.Print.Designer.Model.XmlTrans.TextXmlTrans','fromXml'),
@('Kingdee.BOS.NotePrinting.ReportOne.Common.Model.IO.StyleCache','CacheStyleFromXml'))) {
$t=$a.GetType($q[0]); foreach($m in $t.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly')|Where-Object{$_.Name -eq $q[1]}){[ILProbe]::Show($m)}
}