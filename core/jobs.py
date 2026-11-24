import copy
from datetime import datetime
import os
from pathlib import Path
import secrets
import threading
import time

from .cache import Cache,fingerprint
from .media import local_path,probe,ffmpeg
from .process import Runner,Cancelled,save_json,load_json
from .settings import validate,DEFAULTS
from .naming import game_name,mode_folder


class Manager:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.cancel=threading.Event();self.worker=None
        self.state=dict(status='idle',message='Escolha sua gravação para começar.',stage='',percent=None,done=0,total=None,eta=None,elapsed=0,plan=None,files=[],log=[])
        self.source=None;self.folder=None;self.info=None;self.settings=None;self.analysis=None;self.segments=[]
        self.started=None;self.stage_started=time.monotonic();self.saved=0.;self.active_action=None
        self.telemetry={};self.preview=None

    def busy(self):return self.worker is not None and self.worker.is_alive()

    @property
    def export_folder(self):
        return Path(self.settings['export_directory']) if self.settings and self.settings.get('export_directory') else self.folder

    def snapshot(self):
        with self.lock:
            result=copy.deepcopy(self.state)
            if self.started and self.busy():result['elapsed']=round(time.monotonic()-self.started,1)
            result.update(busy=self.busy(),telemetry=self.telemetry)
            return result

    def persist(self):
        if self.folder and self.settings:
            save_json(self.folder/'sessao.json',dict(state=self.state,settings=self.settings,info=self.info,source=str(self.source),action=self.active_action))
            save_json(self.root/'last.json',dict(folder=str(self.folder)))

    def update(self,**values):
        with self.lock:
            self.state.update(values)
            now=time.monotonic()
            if now-self.saved>.5 or values.get('status') in {'review','done','paused','error'}:
                self.persist();self.saved=now

    def report(self,stage,done,total,message):
        with self.lock:
            now=time.monotonic()
            if stage!=self.state.get('stage'):
                self.stage_started=now
                self.state['log']=(self.state.get('log',[])+[message])[-80:]
            elapsed=now-self.stage_started
            eta=(total-done)*elapsed/done if total and done>0 and elapsed>1 and done<total else None
            self.update(stage=stage,done=round(done,3),total=total,percent=round(100*done/total,1) if total else None,
                eta=round(eta,1) if eta is not None else None,message=message)

    def _start(self,operation,action):
        if self.busy():raise ValueError('Aguarde ou interrompa a operação atual.')
        self.cancel.clear();self.active_action=action;self.started=time.monotonic()
        def task():
            try:operation()
            except Cancelled as exc:self.update(status='paused',message=str(exc),eta=None)
            except Exception as exc:self.update(status='error',message=str(exc),eta=None)
            finally:
                with self.lock:
                    self.state['elapsed']=round(time.monotonic()-self.started,1);self.persist()
        self.worker=threading.Thread(target=task,name='studio-worker',daemon=True);self.worker.start()

    def analyze(self,data):
        with self.lock:
            if self.busy():raise ValueError('Uma operação já está em andamento.')
            settings=validate(data)
            source=local_path(data.get('input'),file=True)
            output=local_path(data.get('output'))
            if output.exists() and not output.is_dir():raise ValueError('A saída precisa ser uma pasta.')
            settings['game_name']=game_name(settings['game_name'] or source.stem)
            project=(output/settings['game_name']).resolve()
            if not project.is_relative_to(output):raise ValueError('A pasta do jogo aponta para fora da saída escolhida.')
            exports=project/mode_folder(settings)
            if not exports.resolve().is_relative_to(project):raise ValueError('A pasta do modo aponta para fora da pasta do jogo.')
            exports.mkdir(parents=True,exist_ok=True)
            settings['export_directory']=str(exports)
            folder=project/'.studio'/(datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+secrets.token_hex(3))
            folder.mkdir(parents=True,exist_ok=False)
            self.source=source;self.folder=folder;self.settings=settings;self.info=None;self.segments=[];self.preview=None
            self.state.update(status='analyzing',plan=None,files=[],preview=None,log=[],encoder=None,folder=str(exports),project_folder=str(project),settings=settings,input=str(source),message='Lendo a gravação',percent=None,stage='Preparação')
            self._start(self._analyze,'analysis')

    def _analyze(self):
        from .scanner import analyze
        from .transcription import transcribe
        from modes.plan import create
        runner=Runner(self.cancel,self.report)
        self.info=probe(self.source,runner)
        for name in ['audio_track','render_audio_track']:
            if self.info['audio'] and self.settings[name]>=len(self.info['audio']):raise ValueError('Faixa de áudio inexistente: '+name)
        cache=Cache(self.root/'cache',self.source)
        self.settings['source_identity']=cache.identity
        self.update(info=self.info,settings=self.settings)
        self.analysis=analyze(self.info,cache,runner,sample_seconds=self.settings['sample_seconds'],audio_track=self.settings['audio_track'],decode='cpu' if self.settings['encoder']=='cpu' else 'auto')
        self.segments,device=transcribe(self.info,cache,runner,self.settings)
        runner.check()
        save_json(self.folder/'analysis.json',self.analysis)
        save_json(self.folder/'transcript.json',self.segments)
        plan=create(self.analysis,self.segments,self.info,self.settings,self.folder)
        if fingerprint(self.source)!=cache.identity:raise ValueError('A fonte mudou durante a análise. Reinicie com o arquivo finalizado.')
        self.update(status='review',plan=plan,percent=None,eta=None,cache=dict(hits=cache.hits,misses=cache.misses),
            engine=dict(decoder=self.analysis['decoder'],transcription=device),message='Plano pronto para revisão. Aprove ou rejeite os trechos antes de renderizar.')

    def begin_render(self,data):
        from modes.plan import validate as validate_plan
        with self.lock:
            if self.busy() or self.info is None or self.settings is None:raise ValueError('Analise uma gravação e aguarde o plano.')
            if self.state['status'] not in {'review','paused','error','done'}:raise ValueError('Plano indisponível.')
            plan=validate_plan(copy.deepcopy(data.get('plan') or self.state['plan']),self.info['duration'],self.settings['mode'])
            # Encoder/quality are render options; changing them never rescans the source.
            checked=validate({**self.settings,**{key:data[key] for key in ['encoder','quality'] if key in data}})
            self.settings.update(encoder=checked['encoder'],quality=checked['quality'])
            self.state.update(status='rendering',plan=plan,settings=self.settings,encoder=None,percent=None,message='Preparando renderização')
            save_json(self.folder/'plano_render.json',plan)
            self._start(self._render,'render')

    def _render(self):
        from render.video import render
        files,encoder=render(self.source,self.info,self.state['plan'],self.settings,self.folder,Runner(self.cancel,self.report),self.segments,
            on_encoder=lambda encoder:self.update(encoder=encoder))
        self.update(status='done',files=files,percent=100,eta=None,encoder=encoder,message='Vídeos concluídos: metadados, timestamps e decodificação completa aprovados.')

    def restore(self):
        with self.lock:
            if self.busy():raise ValueError('Uma operação está em andamento.')
            folder=Path(load_json(self.root/'last.json')['folder']).resolve()
            record=load_json(folder/'sessao.json')
            source=local_path(record['source'],file=True)
            settings=validate(record['settings'])
            identity=record['settings'].get('source_identity')
            if identity and fingerprint(source)!=identity:raise ValueError('A fonte mudou; a sessão não pode ser retomada.')
            settings['source_identity']=identity
            if record['settings'].get('export_directory'):
                settings['export_directory']=str(local_path(record['settings']['export_directory']))
            self.source=source;self.folder=folder;self.settings=settings;self.info=record['info']
            self.state=record['state'];self.state.update(status='paused',message='Sessão recuperada; clique em Retomar.',settings=settings)
            self.active_action=record['action']
            self.segments=load_json(folder/'transcript.json') if (folder/'transcript.json').is_file() else []
            self.persist()

    def resume(self):
        with self.lock:
            if self.busy() or not self.folder:raise ValueError('Não há operação interrompida para retomar.')
            if self.active_action=='render' and self.state.get('plan'):
                self.update(status='rendering');self._start(self._render,'render')
            else:
                self.update(status='analyzing');self._start(self._analyze,'analysis')

    def make_preview(self,data):
        with self.lock:
            if self.busy() or not self.info:raise ValueError('Aguarde a análise antes da prévia.')
            start,end=float(data['start']),float(data['end'])
            import math
            if not all(map(math.isfinite,(start,end))) or not 0<=start<end<=self.info['duration']:raise ValueError('Intervalo de prévia inválido.')
            end=min(end,start+60)
            self.preview=None;self.update(preview=None)
            def operation():
                path=self.folder/'preview.mp4';pending=self.folder/'preview.partial.mp4'
                runner=Runner(self.cancel,self.report)
                command=ffmpeg()+['-ss',str(start),'-i',str(self.source),'-t',str(end-start),'-map','0:v:0','-map',f"0:a:{self.settings['render_audio_track']}?",'-vf','scale=min(960\\,iw):-2','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(pending)]
                runner.run(command,total=end-start,stage='Prévia local de até 60 segundos')
                pending.replace(path);self.preview=path
                self.update(status='review',preview=True,message=f'Prévia pronta: {start:g}s a {end:g}s. A exportação usa a qualidade escolhida.')
            self.update(status='previewing');self._start(operation,'preview')

    def download_model(self,data):
        with self.lock:
            if self.busy():raise ValueError('Aguarde a operação atual.')
            model=data.get('model','small')
            if model not in {'tiny','base','small','medium'}:raise ValueError('Modelo inválido.')
            target=self.root/'models'/model
            def operation():
                import sys
                Runner(self.cancel,self.report).run([sys.executable,'-X','utf8','-m','core.download_model',model,str(target)])
                self.update(status='idle',downloaded_model=str(target),message='Modelo local pronto. Ative Transcrição e selecione esta pasta.')
            self.update(status='downloading',message='Baixando apenas o modelo gratuito. Nenhuma gravação é enviada.',percent=None,total=None,eta=None)
            self._start(operation,'model')
