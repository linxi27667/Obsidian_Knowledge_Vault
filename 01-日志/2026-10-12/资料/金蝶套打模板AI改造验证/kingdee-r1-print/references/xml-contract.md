# 已验证的 XML 契约

本例是 r1-print 6.3.0 文件，验证使用本机 Kingdee.BOS.NotePrinting 9.0.553.10。其他版本须以用户导出的有效文件为准。

## 根与样式

DocRoot 中保留 Parameters、DataSources、Styles、Layers、Report、PrintInfo。DataSources 中 Reference、Params、Associate 描述取数和关联；不能因为改纸型或文字就重建它们。

~~~xml
<Styles version="1.0">
  <Style id="0">...</Style>
</Styles>
<Report type="r1-print" version="6.3.0">
  <Page id="page1" width="2000" height="1380">
    <Sub-objects>...</Sub-objects>
  </Page>
</Report>
~~~

在 Python ElementTree 中，Element.clear() 同时移除子节点、属性、文本和尾部文字。正确做法是先复制属性，再清空，再恢复；Report 的 type/version 也要保留。本案缺失 Styles@version 让 StyleParser.Upgrade 抛出 NullReferenceException。

Style 的 Font、Borders、Interior、Alignment、Protection、NumberFormat 从有效源模板复制。styleId 必须指向已有样式。边框本案采用 Single，透明填充及其他属性继续复用源模板。

## 文本、二维码与版面

Text 的位置尺寸是 x/y/width/height。本例按 0.1 mm 理解坐标，原 A4 模板内容宽 1720、高 2470，与 19 mm 左右和 25 mm 上下边距相符。仍应对目标金蝶版本用纸型设置和实际预览核对。

静态 Data 的文本和 CDATA 在本案都可原生读取，7 个空 Data 节点也未阻止导入。它们不是本次根因。正式绑定通常使用 Data 的 dataSource/bindField，动态字段有 Type；保留原有形式与元数据，不从中文字段标签猜 API Key。

Barcode 的 EncodeType 在本机经典 QR 路径中是 Qrcode，大小写应准确。QR Code、QRCode、QR_CODE 等探测值不等同。编码内容必须按业务用途定义；本例仅编码固定样本单号，未建立扫码报工或业务导航功能。

本例 A5 横向，物理 210×148 mm，四边距 5 mm，Page 内容 200×138 mm；此纸型是 Demo 的假设。Header/Footer 设为 0，页码用静态 Text，因此只有第 1 页，不具备动态分页计数。红色“改动后”是参考图标注，未印入模板。

## 原生读取器的调用条件

- 必须实际启动 Windows PowerShell 5.1 的 powershell.exe，让库运行在 .NET Framework CLR；仅指定工具 shell 字段不证明已切换。检查 PSVersionTable 与 Environment.Version。
- R1PrintXmlReader.FromXml 的第二参使用非空 NoteDataXmlTrans。
- SetXmlTransChain 接受工具箱对象列表，例如 ToolboxTextObject、ToolboxBarcode、ToolboxCurrencyObject。列表只放 getXmlTrans() 返回的转换器会导致控件被跳过；能返回模型而无异常并不代表全部对象已导入。
- Writer 的 setXmlTransChain 使用同样列表。读取前后比较数量、ID、类型、位置、静态内容和绑定。
- R1PBarcode_W2V.loadImage 是静态方法，反射查询必须包含 Static；仅筛 Instance 会找不到方法。本例静态 Qrcode 可生成 85×85 像素图。
- 原生辅助脚本只覆盖 Text/Barcode/Currency；未知控件必须明确报错，不能悄悄略过。
