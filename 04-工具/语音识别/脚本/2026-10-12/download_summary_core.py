import urllib.request,json,pathlib,concurrent.futures,hashlib,zipfile,tarfile,io,sys
from packaging.tags import sys_tags
from packaging.utils import parse_wheel_filename
BASE=pathlib.Path(__file__).parent/'summarylocal';BASE.mkdir(exist_ok=True)
def fetch(project):
    for attempt in range(4):
        try:
            metadata=json.load(urllib.request.urlopen(f'https://pypi.org/pypi/{project}/json',timeout=20));break
        except Exception:
            if attempt==3:raise
    choices=metadata['urls'];supported=set(sys_tags())
    item=next((x for x in choices if x['filename'].endswith('.whl') and supported.intersection(parse_wheel_filename(x['filename'])[3])),next(x for x in choices if x['packagetype']=='sdist'))
    size=item['size'];url=item['url'];chunk=1024*1024
    def part(start):
        end=min(start+chunk,size)-1
        for attempt in range(3):
            try:
                req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'})
                with urllib.request.urlopen(req,timeout=35) as r:
                    data=r.read()
                    if len(data)==size and start==0:return start,data
                    if len(data)!=end-start+1:raise RuntimeError('Unexpected response size')
                    return start,data
            except Exception:
                if attempt==2:raise
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:parts=list(pool.map(part,range(0,size,chunk)))
    data=b''.join(x[1] for x in sorted(parts))
    if hashlib.sha256(data).hexdigest()!=item['digests']['sha256']:raise RuntimeError('Package checksum differs')
    package=BASE/item['filename'];package.write_bytes(data)
    if item['filename'].endswith('.whl'):
        with zipfile.ZipFile(io.BytesIO(data)) as z:z.extractall(BASE)
    else:
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as t:
            for member in t.getmembers():
                parts=pathlib.PurePosixPath(member.name).parts
                if len(parts)>1 and parts[1]=='jieba':
                    member.name='/'.join(parts[1:]);t.extract(member,BASE,filter='data')
    print('Ready',project,metadata['info']['version'],size,'bytes',flush=True)
projects=sys.argv[1:] or ['sumy','jieba']
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for f in [pool.submit(fetch,p) for p in projects]:f.result()
