# 修改、验证、排错和交付的完整流程

## 1. 确认输入和范围

取得已知可导入的原模板、目标样张和业务对象说明。阅读本地项目/知识库规则。用户要求直接编辑且已经备份时不重复请求授权；仍在 work 或明确备份目录保存改动前副本与 SHA-256，避免排错时失去比较基准。

先读取字节头：XML 文件以 <?xml 开始。PowerShell 7 不接受 Get-Content -Encoding Byte；用 IO.File.ReadAllBytes。读取模板的 DataSources 和 Data 绑定，比较参考图的业务对象。采购发票骨架不能直接证明可打印生产工单。Demo 可以保留骨架数据源、以静态内容试排版；正式版要取得工序计划的真实骨架和字段。

## 2. 抽取目标布局

列出：标题、九个订单/物料/日期字段、二维码、表头与明细、备注、签收栏、页码。测量相对坐标、列宽、行高，确定哪些空白是人工填写区。先对照纸型和边距，不能把截图尺寸直接当实物纸张。区别红色标注、远程工具按钮、设计器选择框与需要打印的内容。

静态案例可用 assets/operation-demo-layout.json 修改；它用通用示例数据，具体工厂样张在本次完整流程中嵌入，已导入文件保留在该流程记载的本机工作备份中。多个明细行的正式版应使用数据表格及正确数据源/关联/过滤，不能把单行 Demo 推广为正式循环表格。

## 3. 创建候选并做预检

使用系统可用的 Python；路径带空格时正确引用：

~~~powershell
python scripts/build_layout_demo.py --source ORIGINAL.r1-print --output work/candidate.r1-print
python scripts/validate_xml.py work/candidate.r1-print --report work/xml-check.json
~~~

build_layout_demo.py 要求输入和输出不同。它保留源 Styles 的属性、源 Report 属性和全部 DataSources，以原有效样式为基底建立 Demo。所有文字/二维码内容固定，页码固定。做正式模板时应单独保留绑定和循环结构，不运行这个静态重建脚本覆盖正式报表。

预检包括根节点、版本、ID 唯一、样式引用、数据源引用、边界和绑定清单。预检通过仍不能宣称设计器可导入。

## 4. 原生解析与重新序列化

指定实际 Windows PowerShell 5.1 路径；从 pwsh 中显式启动：

~~~powershell
& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File scripts/validate_native.ps1 -TemplatePath work/candidate.r1-print -ReportPath work/native-check.json -RoundtripDirectory work/native-roundtrip -QrImageDirectory work/qr
~~~

如果金蝶安装位置不同，使用 AssemblyPath 指向匹配客户端的 Kingdee.BOS.NotePrinting.dll。依赖加载错误时不复制未知 DLL、不改变生产服务器；确认运行时和同目录依赖，保存失败信息。

同一个原生校验器先检查原文件，再检查候选。本例原文件有 7 个对象、候选有 37 个；其他模板按自身实际数量核对全部对象被读取，不能只返回空页面。脚本要求 ID/数量、位置、Data 内容与绑定保持一致；静态二维码做原生图像生成。动态字段只能证明格式被读取，正确取数需业务预览。

## 5. 导入空引用的排查

保留失败版和截图，查看“详细”信息或在原生校验器复现堆栈。若命中本案 StyleParser.Upgrade：

~~~powershell
python scripts/repair_styles_version.py --source work/failed.r1-print --reference ORIGINAL.r1-print --output work/fixed.r1-print
python scripts/validate_xml.py work/fixed.r1-print
~~~

再次原生校验固定候选。确认只恢复了原有效 Styles 版本、全部控件仍在，再按用户授权替换目标或交付。根因不在样式版本时继续定位实际控件/数据源/纸型/脚本；不要盲目尝试同一修补。

## 6. 视觉与设计器确认

用候选 XML 生成或查看版式模拟预览，明确标记“模拟”。本例曾用 Pillow、宋体字体及金蝶原生生成的 QR 图绘制静态预览，不能将它当作原生打印截图。

用户在设计器导入后查看标题、列顺序、文本换行、边框、二维码、备注、签收栏、页码。截图验证的是载入与显示，不自动证明保存发布、绑定、分页、扫码功能或实物打印。只读预置模板应按业务需要复制成可编辑模板；正式生产模板应基于工序计划业务对象配置并预览真实数据。

## 7. 一份流程与同步

在对应事项的完整流程 Markdown 中集中记录操作、踩坑、原因、解决、验证、环境版本和纸型假设，必要图片嵌入对应步骤。日志通俗解释结果并直接跳转，流程返回日志；不再拆附件目录、诊断或验证笔记。具体分工遵循知识库 `09-规则/Obsidian日志Skill.md`。

源模板、失败/修复版本和完整检查结果默认保留工作目录或既有资料包，流程写清来源位置与关键结论；可复用脚本和 Skill 资源保存在隐藏技能目录。用户明确要求额外原件归档时按实际需求保存；需要逐字节回查的样本，可在其实际归档位置设置局部 .gitattributes 的 -text，并比较暂存 blob 与原始 SHA-256，避免 Git 自动换行改变证据。

用户授权 Git 推送时检查分支、远程、已有工作区和暂存区，暂存本任务文件并回读提交内容，推送后比较远程分支与本地提交。不要把其他任务的改动、凭据、金蝶闭源 DLL、缓存或虚拟环境放进仓库。
