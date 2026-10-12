import sys,pathlib,json,time,re,concurrent.futures
BASE=pathlib.Path(r'C:\Users\juncheng.liu\.codex\tmp\audio-dialogue-20261011')
sys.path.insert(0,str(BASE/'pythonpkgs'))
import av,numpy as np,sherpa_onnx
SOURCE=pathlib.Path(r'C:\Users\juncheng.liu\Documents\xwechat_files\wxid_ju03a9g7z3z622_c26b\msg\file\2026-10')
WORK=pathlib.Path(__file__).parent
DEST=pathlib.Path(r'C:\Users\juncheng.liu\Desktop\对话总结\2026-10-12 余总与PMC面试')
SR=16000
def stamp(t):
    return f'{int(t)//3600:02d}:{int(t)%3600//60:02d}:{int(t)%60:02d}'
def run(name):
    work=WORK/name;work.mkdir(parents=True,exist_ok=True)
    c=av.open(str(SOURCE/(name+'.m4a')))
    resampler=av.AudioResampler(format='fltp',layout='mono',rate=SR)
    pieces=[]
    for frame in c.decode(audio=0):
        pieces.extend(out.to_ndarray().flatten() for out in resampler.resample(frame))
    pieces.extend(out.to_ndarray().flatten() for out in resampler.resample(None))
    audio=np.concatenate(pieces).astype(np.float32);c.close();del pieces
    np.save(work/'audio.npy',audio)
    duration=len(audio)/SR
    (work/'metadata.json').write_text(json.dumps({'source':str(SOURCE/(name+'.m4a')),'duration_seconds':duration,'date_user_provided':'2026-10-12','sample_rate':SR},ensure_ascii=False,indent=2),encoding='utf-8')
    print(name,'duration',round(duration,2),flush=True)
    recognizer=sherpa_onnx.OfflineRecognizer.from_sense_voice(model=str(BASE/'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/model.int8.onnx'),tokens=str(BASE/'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/tokens.txt'),language='zh',use_itn=True,num_threads=3,debug=False)
    ranges=[];start=0
    while start<len(audio):
        if len(audio)-start<SR*30:end=len(audio)
        else:
            lo=start+SR*20;hi=min(start+SR*28,len(audio));width=SR//20
            a=audio[lo:hi];a=a[:len(a)//width*width].reshape(-1,width)
            rms=np.sqrt(np.mean(a*a,axis=1));smooth=np.convolve(rms,np.ones(5)/5,mode='valid')
            end=lo+(int(np.argmin(smooth))+2)*width
        ranges.append((start,end));start=end
    entries=[]
    with (work/'asr.jsonl').open('w',encoding='utf-8') as f:
        for i,(start,end) in enumerate(ranges):
            ps=max(0,start-int(.25*SR));pe=min(len(audio),end+int(.25*SR))
            stream=recognizer.create_stream();stream.accept_waveform(SR,audio[ps:pe]);recognizer.decode_stream(stream);result=stream.result
            e={'index':i,'start':start/SR,'end':end/SR,'padded_start':ps/SR,'text':result.text,'tokens':result.tokens,'timestamps':[ps/SR+x for x in result.timestamps]}
            entries.append(e);f.write(json.dumps(e,ensure_ascii=False)+'\n');f.flush()
            if i%10==0 or i==len(ranges)-1:print(name,'SenseVoice',i+1,'/',len(ranges),flush=True)
    del recognizer
    (work/'asr.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8')
    para=sherpa_onnx.OfflineRecognizer.from_paraformer(paraformer=str(BASE/'paraformer/model.int8.onnx'),tokens=str(BASE/'paraformer/tokens.txt'),num_threads=3,debug=False)
    verify=[]
    with (work/'paraformer.jsonl').open('w',encoding='utf-8') as f:
        for i,e in enumerate(entries):
            stream=para.create_stream();stream.accept_waveform(SR,audio[int(e['padded_start']*SR):min(len(audio),int((e['end']+.25)*SR))]);para.decode_stream(stream)
            v={'index':i,'start':e['start'],'end':e['end'],'text':stream.result.text};verify.append(v);f.write(json.dumps(v,ensure_ascii=False)+'\n');f.flush()
            if i%10==0 or i==len(entries)-1:print(name,'Paraformer',i+1,'/',len(entries),flush=True)
    del para
    (work/'paraformer.json').write_text(json.dumps(verify,ensure_ascii=False,indent=2),encoding='utf-8')
    config=sherpa_onnx.OfflineSpeakerDiarizationConfig(segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(BASE/'sherpa-onnx-pyannote-segmentation-3-0/model.onnx'),window_shift_ratio=.2),num_threads=3),embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(BASE/'embedding.onnx'),num_threads=3),clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1,threshold=.5),min_duration_on=.2,min_duration_off=.3)
    diar=sherpa_onnx.OfflineSpeakerDiarization(config);prev=[-1]
    def progress(n,total):
        percent=int(n/total*100)
        if percent//20!=prev[0]//20:prev[0]=percent;print(name,'speaker clustering',percent,'%',flush=True)
        return 0
    result=diar.process(audio,callback=progress).sort_by_start_time()
    ds=[{'start':x.start,'end':x.end,'speaker':x.speaker} for x in result]
    (work/'speakers.json').write_text(json.dumps(ds,ensure_ascii=False,indent=2),encoding='utf-8')
    turns=[]
    for e in entries:
        for tok,t in zip(e['tokens'],e['timestamps']):
            if t<e['start'] and e['index']>0:continue
            if t>=e['end'] and e['index']<len(entries)-1:continue
            if re.fullmatch(r'[\s，。？！、；：,.?!:;]+',tok):speaker=turns[-1]['speaker'] if turns else -1
            else:
                active=[s for s in ds if s['start']<=t+.06<=s['end']]
                if active:speaker=min(active,key=lambda s:abs((s['start']+s['end'])/2-t))['speaker']
                elif ds:
                    near=min(ds,key=lambda s:min(abs(s['start']-t),abs(s['end']-t)))
                    speaker=near['speaker'] if min(abs(near['start']-t),abs(near['end']-t))<1 else -1
                else:speaker=-1
            if turns and turns[-1]['speaker']==speaker and t-turns[-1]['end']<5:turns[-1]['text']+=tok;turns[-1]['end']=t
            else:turns.append({'start':t,'end':t,'speaker':speaker,'text':tok})
    (work/'turns.json').write_text(json.dumps(turns,ensure_ascii=False,indent=2),encoding='utf-8')
    DEST.mkdir(parents=True,exist_ok=True)
    intro=f'{name}｜完整机器转写\n录音时长：{stamp(duration)}\n活动日期：2026-10-12（用户说明）\n转写：本机 sherpa-onnx / SenseVoice；另用 Paraformer 做独立识别对照。\n说话人编号为机器聚类，不对应已经确认的姓名；两段录音的编号分别计算。噪声、重叠发言、人名及专业词可能识别有误。本稿保留原始机器结果，未逐句人工听校。\n\n'
    lines=[f'[{stamp(t["start"])}—{stamp(t["end"])}] 说话人{t["speaker"]+1 if t["speaker"]>=0 else "待核"}：{t["text"]}' for t in turns]
    (DEST/(name+' 完整机器转写.txt')).write_text(intro+'\n\n'.join(lines)+'\n',encoding='utf-8-sig')
    comparison=[f'[{stamp(e["start"])}—{stamp(e["end"])}]\nSenseVoice：{e["text"]}\nParaformer：{v["text"]}\n' for e,v in zip(entries,verify)]
    (DEST/(name+' 双模型转写对照.txt')).write_text(intro+'\n'.join(comparison),encoding='utf-8-sig')
    (DEST/(name+' 分段文字稿.txt')).write_text(intro+'\n\n'.join(f'[{stamp(e["start"])}—{stamp(e["end"])}] {e["text"]}' for e in entries)+'\n',encoding='utf-8-sig')
    print(name,'FINISHED','speakers',len(set(x['speaker'] for x in ds)),'characters',sum(len(e['text']) for e in entries),'segments',len(entries),flush=True)
if __name__=='__main__':
    names=sys.argv[1:] or ['仓库物料管理相关讨论','企业生产运营相关讨论']
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(names)) as pool:
        for f in [pool.submit(run,n) for n in names]:f.result()
