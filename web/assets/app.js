'use strict';
const $=id=>document.getElementById(id),TOKEN=window.LOCAL_TOKEN;
let state={},plan=null,planKey='',polling=false,previewKey='',resultsKey='';
const fmt=x=>x===null||x===undefined?'—':new Date(Math.max(0,Math.round(x))*1000).toISOString().slice(11,19);
const media=path=>path+'?token='+encodeURIComponent(TOKEN);
async function api(path,data){const r=await fetch('/api/'+path,{method:data===undefined?'GET':'POST',headers:{'X-Local-Token':TOKEN,'Content-Type':'application/json'},...(data===undefined?{}:{body:JSON.stringify(data)})});const result=await r.json();if(!r.ok)throw new Error(result.error||'Falha na operação');return result;}
function error(e){$('error').textContent=e.message||String(e);$('error').hidden=false;setTimeout(()=>$('error').hidden=true,15000);}
function mode(){const value=document.querySelector('[name=mode]:checked').value;document.querySelectorAll('[data-mode]').forEach(el=>el.hidden=el.dataset.mode!==value);if(value!=='shorts')$('captions').checked=false;}
document.querySelectorAll('[name=mode]').forEach(el=>el.addEventListener('change',mode));mode();
const numbers=['episodes','episode_minutes','short_seconds','sensitivity','minimum_score','sample_seconds','context_seconds','min_idle','batch_size','audio_track','render_audio_track','speech_weight','cue_weight'];
const strings=['game_name','quality','encoder','gameplay_mode','selection_style','model_path','language','transcription_device','compute_type'];
function config(){const out={input:$('input').value,output:$('output').value,mode:document.querySelector('[name=mode]:checked').value};numbers.forEach(id=>out[id]=Number($(id).value));strings.forEach(id=>out[id]=$(id).value);['transcribe','vad','captions'].forEach(id=>out[id]=$(id).checked);return out;}
function fill(settings){if(!settings)return;for(const id of [...numbers,...strings])if(settings[id]!==undefined)$(id).value=settings[id];for(const id of ['transcribe','vad','captions'])$(id).checked=!!settings[id];const radio=document.querySelector(`[name=mode][value="${settings.mode}"]`);if(radio)radio.checked=true;mode();$('sensitivity_value').value=$('sensitivity').value;}
$('sensitivity').addEventListener('input',()=>$('sensitivity_value').value=$('sensitivity').value);
document.querySelectorAll('[data-browse]').forEach(el=>el.onclick=async()=>{el.disabled=true;try{const r=await api('browse',{kind:el.dataset.browse==='input'?'file':'folder'});if(r.path)$(el.dataset.browse).value=r.path;}catch(e){error(e);}finally{el.disabled=false;}});
$('config').onsubmit=async event=>{event.preventDefault();try{await api('analyze',config());planKey='';resultsKey='';previewKey='';await poll();}catch(e){error(e);}};
$('cancel').onclick=()=>api('cancel',{}).catch(error);
$('resume').onclick=()=>api('resume',{}).then(poll).catch(error);
$('restore').onclick=async()=>{try{await api('restore',{});planKey='';await poll();fill(state.settings);$('input').value=state.input||'';}catch(e){error(e);}};
$('download').onclick=()=>api('model',{model:$('download_size').value}).then(poll).catch(error);
$('open').onclick=()=>api('open',{}).catch(error);
function renderPlan(p){
 plan=structuredClone(p);$('timeline').replaceChildren();$('plan-note').textContent=p.note||'';
 $('render_encoder').value=state.settings?.encoder||'nvenc';$('render_quality').value=state.settings?.quality||'high';
 let total=0,count=0;
 p.episodes.forEach((episode,ei)=>{
  const box=document.createElement('div');box.className='episode';const title=document.createElement('h3');title.textContent=`${state.settings?.mode==='shorts'?'Short':'Vídeo'} ${ei+1} · ${fmt(episode.duration)}`;box.append(title);
  episode.segments.forEach((row,si)=>{
   total+=row.end-row.start;count++;
   const cut=document.createElement('div');cut.className='cut';
   const approved=document.createElement('input');approved.type='checkbox';approved.checked=true;approved.setAttribute('aria-label',`Aprovar trecho ${si+1} do vídeo ${ei+1}`);approved.dataset.e=ei;approved.dataset.s=si;cut.append(approved);
   const text=document.createElement('div');text.className='reason';text.textContent=row.reason||'Trecho selecionado';const hint=document.createElement('small');hint.textContent=`Original: ${fmt(row.start)} → ${fmt(row.end)}`;text.append(hint);cut.append(text);
   for(const field of ['start','end']){const label=document.createElement('label');label.textContent=field==='start'?'Início (s)':'Fim (s)';const input=document.createElement('input');input.type='number';input.min=0;input.step='.001';input.value=row[field].toFixed(3);input.onchange=()=>plan.episodes[ei].segments[si][field]=Number(input.value);label.append(input);cut.append(label);}
   const preview=document.createElement('button');preview.textContent='▶ Prévia';preview.type='button';preview.className='preview-button';preview.onclick=()=>{const r=plan.episodes[ei].segments[si];api('preview',{start:r.start,end:r.end}).then(poll).catch(error);};cut.append(preview);box.append(cut);
  });$('timeline').append(box);
 });
 $('plan-summary').textContent=`${p.episodes.length} vídeos · ${count} trechos · ${fmt(total)}`;
 const bitrate=Number(state.info?.size||0)*8/Math.max(1,Number(state.info?.duration||1));const guess=total*Math.max(bitrate,8e6)/8/1024**3;
 $('disk').textContent=`Espaço estimado: ~${guess.toFixed(2)} GB nos finais. Intermediários de áudio e vídeo exigem espaço adicional; Ultra pode ultrapassar esta estimativa.`;
}
$('all').onclick=()=>document.querySelectorAll('.cut input[type=checkbox]').forEach(el=>el.checked=true);
$('none').onclick=()=>document.querySelectorAll('.cut input[type=checkbox]').forEach(el=>el.checked=false);
$('render').onclick=()=>{try{if(!plan)throw new Error('Analise uma gravação primeiro.');const selected=structuredClone(plan);selected.episodes=selected.episodes.map((ep,ei)=>({...ep,segments:ep.segments.filter((_,si)=>document.querySelector(`.cut input[data-e="${ei}"][data-s="${si}"]`)?.checked)})).filter(ep=>ep.segments.length);if(!selected.episodes.length)throw new Error('Aprove ao menos um trecho.');api('render',{plan:selected,encoder:$('render_encoder').value,quality:$('render_quality').value}).then(poll).catch(error);}catch(e){error(e);}};
function update(s){
 state=s;$('message').textContent=s.message;$('stage').textContent=s.stage||'Aguardando';$('status').textContent=({idle:'PRONTO',analyzing:'ANALISANDO',review:'REVISÃO',rendering:'RENDERIZANDO',done:'CONCLUÍDO',paused:'INTERROMPIDO',error:'ERRO',previewing:'PRÉVIA',downloading:'MODELO'})[s.status]||s.status;
 $('percent').textContent=s.percent===null?'—':`${Number(s.percent).toFixed(1)}%`;
 if(s.percent===null)$('progress').removeAttribute('value');else $('progress').value=s.percent;
 $('units').textContent=s.total?`${Number(s.done||0).toFixed(1)} / ${Number(s.total).toFixed(1)} segundos processados nesta etapa`:'O percentual aparece quando a etapa possui progresso mensurável.';
 $('elapsed').textContent=fmt(s.elapsed);$('eta').textContent=fmt(s.eta);
 $('render-device').textContent=s.encoder==='h264_nvenc'?'Codificador: GPU NVIDIA · NVENC':s.encoder==='libx264'?'Codificador: CPU · libx264':s.status==='rendering'?'Verificando o codificador solicitado...':'Codificador: será confirmado ao renderizar';
 $('output-path').textContent=s.folder?`Pasta dos vídeos: ${s.folder}`:'';
 const t=s.telemetry||{};$('gpu').textContent=t.gpu_name?`${t.gpu_name}: ${t.gpu_percent}% · ${t.vram_mb} MB`:'GPU —';$('cpu').textContent=`CPU ${t.cpu_percent??'—'}${t.cpu_percent===null||t.cpu_percent===undefined?'':'%'}`;$('ram').textContent=`RAM ${t.ram_percent??'—'}${t.ram_percent===null||t.ram_percent===undefined?'':'%'}`;
 $('cancel').disabled=!s.busy;$('resume').disabled=s.busy||!['paused','error'].includes(s.status);$('restore').disabled=s.busy;
 $('config').querySelectorAll('input,select,button').forEach(el=>el.disabled=!!s.busy);
 $('render').disabled=s.busy;$('render_encoder').disabled=s.busy;$('render_quality').disabled=s.busy;$('all').disabled=s.busy;$('none').disabled=s.busy;document.querySelectorAll('.preview-button,.cut input').forEach(el=>el.disabled=s.busy);
 $('cache').textContent=s.cache?`Cache: ${s.cache.hits} etapas/blocos reutilizados · ${s.cache.misses} calculados` : '';
 $('logs').textContent=(s.log||[]).join('\n');
 if(s.downloaded_model)$('model_path').value=s.downloaded_model;
 if(s.plan){$('review').hidden=false;const key=JSON.stringify(s.plan);if(key!==planKey){planKey=key;renderPlan(s.plan);}}
 else{$('review').hidden=true;plan=null;}
 if(s.preview){const key=s.folder+'|'+s.message;if(previewKey!==key){previewKey=key;$('preview-panel').hidden=false;$('preview').src=media('/api/media/preview')+'&v='+Date.now();}}
 const files=s.files||[];$('results').hidden=!files.length;
 if(files.length){const key=JSON.stringify(files);if(key!==resultsKey){resultsKey=key;$('files').replaceChildren();files.forEach((f,i)=>{const card=document.createElement('article'),video=document.createElement('video');video.controls=true;video.preload='metadata';video.src=media('/api/media/result/'+i);const title=document.createElement('p');title.textContent=f.file.split(/[\\/]/).pop();const text=document.createElement('p');text.textContent=`${fmt(f.duration)} · ${(f.bytes/1024**2).toFixed(1)} MB · Validado`;const link=document.createElement('a');link.href=video.src;link.download=f.file.split(/[\\/]/).pop();link.textContent='Salvar vídeo';card.append(video,title,text,link);$('files').append(card);});}}
}
async function poll(){if(polling)return;polling=true;try{update(await api('status'));}catch(e){$('message').textContent='Conexão local indisponível. Confira a janela do Studio.';}finally{polling=false;}}
api('diagnostics').then(d=>$('diagnostics').textContent=JSON.stringify(d,null,2)).catch(error);
setInterval(async()=>{try{$('diagnostics').textContent=JSON.stringify(await api('diagnostics'),null,2);}catch{}},10000);
poll();setInterval(poll,900);
