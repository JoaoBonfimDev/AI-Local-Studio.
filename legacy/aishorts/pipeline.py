import hashlib,json,subprocess
from pathlib import Path
from . import media,scan,ranking
from .export import digest,export_files

def choose_encoder(cfg):
    if cfg['encoder']!='auto':return cfg['encoder']
    command=[media.ffmpeg(),'-hide_banner','-loglevel','error','-f','lavfi','-i','color=s=128x128:r=1','-frames:v','1','-c:v','h264_nvenc','-f','null','-']
    return 'h264_nvenc' if subprocess.run(command,capture_output=True).returncode==0 else 'libx264'

def captions(segments,clip):
    rows=[];offset=0
    for a,b in clip['parts']:
        for s in segments:
            if s.get('language')!='pt' or s.get('avg_logprob',-2)<-.8 or s.get('no_speech_prob',1)>.5:continue
            words=[{'start':max(a,w['start'])-a+offset,'end':min(b,w['end'])-a+offset,'text':w['text']} for w in s.get('words',[]) if a<=(w['start']+w['end'])/2<b]
            if words:rows.append({'start':words[0]['start'],'end':words[-1]['end'],'text':s['text'],'words':words})
        offset+=b-a
    return rows

def verify(files,clips,folder,progress=None):
    import av
    results=[]
    for path,c in zip(files,clips):
        with av.open(str(path)) as video:
            v=video.streams.video[0];seconds=video.duration/av.time_base
            if (v.width,v.height)!=(1080,1920) or len(video.streams.audio)!=1:raise ValueError(f'Formato inválido: {path}')
            if abs(seconds-sum(b-a for a,b in c['parts']))>.25:raise ValueError(f'Duração incorreta: {path}')
        p=subprocess.run([media.ffmpeg(),'-hide_banner','-loglevel','error','-xerror','-i',str(path),'-f','null','-'],capture_output=True,text=True)
        if p.returncode:raise RuntimeError(p.stderr)
        results.append({'file':str(path),'seconds':seconds,'bytes':path.stat().st_size,'sha256':digest(path),'full_decode_passed':True})
        if progress:progress('verify',100*len(results)/len(files),f'Validando Short {len(results)}/{len(files)}')
    media.save(folder/'verification.json',results);return results

def report(folder,data,files,exported):
    rows=['# Resultado local','','Método: '+data['method'],data.get('warning','Ranking fornecido e validado estruturalmente.'),'',
          '| Posição | Tipo | Nota | Evidência da escolha | Intervalos (segundos) | Arquivo |','|---|---|---|---|---|---|']
    for i,(c,p) in enumerate(zip(ranking.selected(data),files),1):
        target=exported[i-1]['file'] if i<=len(exported) else str(p)
        evidence=c.get('reason','Seleção revisada manualmente.').replace('|','/')
        rows.append(f"| {i} | {c.get('category','manual')} | {c['score']} | {evidence} | {c['parts']} | {target} |")
    rows+=['','API externa: R$ 0. Legendas automáticas sem garantia de identificação do falante.','Exportação confirmada por SHA-256.' if exported else 'Exportação ainda não confirmada.']
    (folder/'report.md').write_text('\n'.join(rows),encoding='utf-8')

def execute(cfg,folder,stage,ranking_file=None,progress=None,require_four=False):
    def notify(name,percent,message):
        if progress:progress(name,percent,message)
    notify('prepare',0,'Conferindo a gravação')
    info=media.inspect(Path(cfg['input']));duration=info['duration']
    media.save(folder/'source.json',info)
    if cfg['audio_track']>=sum(s['type']=='audio' for s in info['streams']) or cfg['render_audio_track']>=sum(s['type']=='audio' for s in info['streams']):raise ValueError('Faixa de áudio inexistente.')
    notify('prepare',100,f'Vídeo validado: {duration/60:.1f} min')
    if stage in ('scan','run'):
        notify('audio',0,'Preparando transcrição de áudio')
        scan.audio(cfg,folder,notify)
        notify('visual',0,'Iniciando varredura visual')
        scan.visuals(cfg,folder,notify)
        if stage=='scan':return
    ranking_path=folder/'ranking.json'
    notify('rank',0,'Calculando as melhores cenas')
    settings_key={k:cfg[k] for k in ('duration_seconds','minimum_score','shorts')}
    settings_key.update(selection_style=cfg.get('selection_style','balanced'),ranking_algorithm=2)
    if ranking_file:
        data=ranking.read(Path(ranking_file))
        if data.get('source_id')!=folder.name:raise ValueError('source_id deve corresponder à execução exibida por inspect.')
        ranking.validate(data,duration)
        if len(data.get('selected',[]))>4 or len(set(data.get('selected',[])))!=len(data.get('selected',[])):raise ValueError('Seleção inválida.')
        if len({c['rank'] for c in data['clips']})!=len(data['clips']):raise ValueError('Ranks duplicados.')
        if not set(data['selected'])<={c['rank'] for c in data['clips']}:raise ValueError('Rank selecionado não existe.')
        chosen=ranking.selected(data)
        if any(ranking.overlap(a['parts'],b['parts']) for i,a in enumerate(chosen) for b in chosen[i+1:]):raise ValueError('Cortes selecionados sobrepostos.')
        for c in data['clips']:c['slug']=f"{c['score']}pts_candidato_{c['rank']:03}"
        data['method']='reviewed_import';data['settings']=settings_key;media.save(ranking_path,data)
    elif stage in ('rank','run'):
        data=ranking.read(ranking_path) if ranking_path.exists() else None
        if data is None or data.get('settings')!=settings_key:
            data=ranking.generate(folder,cfg,duration);data.update(source_id=folder.name,settings=settings_key);ranking.validate(data,duration);media.save(ranking_path,data)
    else:data=ranking.read(ranking_path)
    clips=ranking.selected(data)
    composition=data.get('composition') or {}
    composition_text=' · '.join(f'{value} {key}' for key,value in composition.items() if value)
    notify('rank',100,f'{len(clips)} cortes selecionados'+(f' | {composition_text}' if composition_text else ''))
    if stage=='rank':print(f'{len(clips)} selecionados; ranking: {ranking_path}');return
    if not clips:raise ValueError('Não há candidatos suficientes com evidência. Consulte ranking.json; nenhum corte foi inventado.')
    if require_four and len(clips)!=4:
        raise ValueError(f'Foram encontrados {len(clips)} de 4 Shorts. Reduza a nota mínima, escolha outra gravação ou revise o ranking; não criamos cenas artificiais.')
    segments=ranking.read(folder/'transcript.json');mapped=[captions(segments,c) for c in clips]
    signature=json.dumps([clips,mapped,cfg['render_audio_track'],cfg['label'],cfg['encoder'],cfg.get('quality','ultra'),3],sort_keys=True,ensure_ascii=False)
    out=folder/'renders'/hashlib.sha256(signature.encode()).hexdigest()[:16];out.mkdir(parents=True,exist_ok=True)
    files=[out/f"{c['rank']:02}_{c['slug']}.mp4" for c in clips]
    if stage in ('render','run'):
        from .render import render
        for c,rows in zip(clips,mapped):media.save(out/f"{c['rank']:02}_transcript.json",rows)
        notify('render',0,'Preparando renderização vertical')
        render_cfg=dict(cfg,encoder=choose_encoder(cfg));render(render_cfg,out,clips,notify)
    # Reuse validation only when the exact outputs still match their verified checksums.
    vpath=out/'verification.json';old=ranking.read(vpath) if vpath.exists() else []
    valid=len(old)==len(files) and all(p.exists() and x['sha256']==digest(p) for p,x in zip(files,old))
    notify('verify',0,'Verificando os MP4')
    if not valid:verify(files,clips,out,notify)
    else:notify('verify',100,'MP4 já verificados')
    exported=[];manifest=out/'export.json'
    if stage in ('export','run'):
        notify('export',0,'Copiando para a pasta de saída')
        prior=ranking.read(manifest)['files'] if manifest.exists() else []
        if len(prior)==len(files) and all(Path(x['file']).parent==Path(cfg['export_directory']) and Path(x['file']).is_file() and digest(Path(x['file']))==digest(p) for x,p in zip(prior,files)):
            exported=prior
            notify('export',100,'Exportação anterior conferida')
        else:
            try:exported=export_files(files,cfg['input'],cfg['export_directory'],len(files),manifest,notify)
            except Exception:
                report(folder,data,files,[]);raise
    report(folder,data,files,exported)
    if stage in ('export','run'):notify('done',100,'Shorts prontos para assistir')
    print(f'{len(files)} MP4 verificados. Relatório: {folder / "report.md"}')
    if len(files)<4:print('Menos de quatro candidatos atingiram os critérios; não foram criados cortes extras.')
    return [{**item,'category':clip.get('category','manual'),'title':clip['title'],
             'reason':clip.get('reason','Revisão manual'),
             'quote':clip.get('quote',''),'start':clip.get('start',clip['parts'][0][0]),
             'score':clip['score']} for item,clip in zip(exported,clips)]
