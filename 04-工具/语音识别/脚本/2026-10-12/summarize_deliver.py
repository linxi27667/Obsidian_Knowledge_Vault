import sys,pathlib,json,re,shutil,datetime,hashlib,importlib.metadata
BASE=pathlib.Path(__file__).parent
sys.path.insert(0,str(BASE/'summarylocal'))
import jieba
from sumy.models.dom import Sentence,Paragraph,ObjectDocumentModel
from sumy.summarizers.text_rank import TextRankSummarizer
DEST=pathlib.Path(r'C:\Users\juncheng.liu\Desktop\对话总结\2026-10-12 余总与PMC面试')
DEST.mkdir(parents=True,exist_ok=True)
ASSETS=DEST/'资料';ASSETS.mkdir(exist_ok=True)
TOOLS=DEST/'开源处理脚本';TOOLS.mkdir(exist_ok=True)
def stamp(t):return f'{int(t)//3600:02d}:{int(t)%3600//60:02d}:{int(t)%60:02d}'
class ChineseTokenizer:
    def to_words(self,text):return tuple(w for w in jieba.lcut(text) if re.search(r'[\u4e00-\u9fffA-Za-z0-9]',w))
tokenizer=ChineseTokenizer();summarizer=TextRankSummarizer()
summarizer.stop_words=frozenset('的 了 是 我 你 他 我们 你们 他们 这个 那个 就 就是 对 对吧 是吧 啊 嗯 呃 呢 吗 吧 然后 还有 但是 所以 因为 比如 比较 有 没有 可以 肯定 说 东西 现在 这样 那样 什么 怎么 一个 这些 那些 得 也 都 很 要 会 在 这 那 去 来 很多'.split())
metadata=[];summary=['2026-10-12 余总与PMC面试｜开源程序抽取摘要','', '生成方式：Sumy 0.13.0 TextRank + jieba 0.42.1 中文分词，直接从 SenseVoice 机器转写抽取原句。未用对话模型逐句重写转录或生成本摘要。','本摘要保留机器识别错误与原句口语；算法选句不保证覆盖所有业务重点，现状判断另见“04 现状分析与改进方向.txt”。说话人身份没有可靠确认。','']
for number,name in enumerate(['仓库物料管理相关讨论','企业生产运营相关讨论'],1):
    work=BASE/name;entries=json.loads((work/'asr.json').read_text(encoding='utf-8'));m=json.loads((work/'metadata.json').read_text(encoding='utf-8'))
    intro=f'{name}｜完整文字稿（机器转写）\n活动日期：2026-10-12（用户说明）\n来源：{m["source"]}\n录音时长：{stamp(m["duration_seconds"])}\n识别方式：本机 sherpa-onnx / SenseVoice；Paraformer 独立识别对照放在“资料”目录。\n按时间分段；自动说话人聚类产生过多声纹簇，结果不可靠，不据此标注姓名。问答或重叠发言可能出现在同一时间段。\n本稿是完整机器识别结果，未逐句人工听校；保留口语、疑似错字和断句。专有名词、数字及身份以原录音或人工确认结果为准。\n\n'
    target=DEST/f'{number:02d} {name} 完整文字稿.txt'
    target.write_text(intro+'\n\n'.join(f'[{stamp(e["start"])}—{stamp(e["end"])}] {e["text"]}' for e in entries)+'\n',encoding='utf-8-sig')
    old=DEST/(name+' 双模型转写对照.txt')
    if old.exists():shutil.move(str(old),str(ASSETS/old.name))
    for oldname in [name+' 完整机器转写.txt',name+' 分段文字稿.txt']:
        old=DEST/oldname
        if old.exists():old.unlink()
    shutil.copy2(work/'asr.json',ASSETS/(name+' SenseVoice.json'))
    shutil.copy2(work/'paraformer.json',ASSETS/(name+' Paraformer.json'))
    records=[]
    for e in entries:
        for raw in re.split(r'(?<=[。！？!?；;])',e['text']):
            raw=raw.strip()
            if len(raw)<12 or not re.search(r'[\u4e00-\u9fff]',raw):continue
            records.append((Sentence(raw,tokenizer),e['start'],e['end']))
    doc=ObjectDocumentModel([Paragraph([x[0] for x in records])])
    chosen=summarizer(doc,min(18,len(records)))
    summary.extend([name+'｜全篇重点原句',''])
    selected=[]
    for sentence in chosen:
        s,start,end=next(x for x in records if x[0]==sentence)
        summary.append(f'[{stamp(start)}—{stamp(end)}] {sentence}')
        selected.append({'start':start,'end':end,'text':str(sentence)})
    summary.extend(['','按约2分钟区间补充抽取（帮助保留不同时段内容）',''])
    for start in range(0,int(m['duration_seconds'])+1,120):
        subset=[x for x in records if start<=x[1]<start+120]
        if not subset:continue
        chunk=ObjectDocumentModel([Paragraph([x[0] for x in subset])])
        for sentence in summarizer(chunk,min(2,len(subset))):
            s,a,b=next(x for x in subset if x[0]==sentence)
            summary.append(f'[{stamp(a)}—{stamp(b)}] {sentence}')
    summary.extend(['',''])
    (work/'extractive_summary.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
    metadata.append({**m,'asr_segments':len(entries),'asr_characters':sum(len(e['text']) for e in entries),'source_sha256':hashlib.sha256(pathlib.Path(m['source']).read_bytes()).hexdigest(),'speaker_clustering_usable':False,'summary_algorithm':'Sumy TextRank','summary_count':len(selected),'transcript_file':target.name})
(DEST/'03 开源程序抽取摘要.txt').write_text('\n'.join(summary),encoding='utf-8-sig')
for script in ['process_recordings.py','summarize_deliver.py','download_summary_core.py']:shutil.copy2(BASE/script,TOOLS/script)
record={'processed_date':'2026-10-12','timezone':'Asia/Shanghai','projects':{'sherpa-onnx':'https://github.com/k2-fsa/sherpa-onnx','SenseVoice':'https://github.com/QwenAudio/SenseVoice','Sumy':'https://github.com/miso-belica/sumy','jieba':'https://github.com/fxsjy/jieba'},'pipeline':'PyAV decode -> SenseVoice ASR -> Paraformer independent ASR -> Sumy TextRank extractive summary','models_directory':str(pathlib.Path(r'C:\Users\juncheng.liu\.codex\tmp\audio-dialogue-20261011')),'audio_files':metadata,'limitations':['ASR and extractive summary are machine results; not a human verbatim verification.','Automatic speaker clustering unreliable; delivered transcript retains timestamps and does not assert named speaker identities.','Business analysis in file 04 is a separate interpretation of source text, not an output of TextRank.']}
(ASSETS/'开源处理记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'destination':str(DEST),'recordings':metadata,'summary_characters':len('\n'.join(summary))},ensure_ascii=False,indent=2))
