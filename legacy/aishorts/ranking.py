"""Ranking local por sinais: ação, comentários e observações; sem prometer semântica humana."""
import bisect
import json
import math
import re
import unicodedata

LIMITS = {'visual':25,'reacoes':25,'entretenimento':20,'narrativa':15,'qualidade':10,'originalidade':5}
KINDS = ('acao','comentario','observacao')
STYLES = {
    'balanced': ('acao','comentario','observacao','acao'),
    'action': ('acao','acao','acao','comentario'),
    'commentary': ('comentario','comentario','acao','observacao'),
    'observation': ('observacao','observacao','comentario','acao'),
}

# Linguagem espontânea em PT-BR: são indícios, não provas sobre quem está falando.
REACTIONS = ('caramba','nossa','nao acredito','meu deus','que lindo','que fofo',
             'engracado','haha','hahaha','ufa','caralho','eita','mano','meu pai',
             'que loucura','ta maluco','meu amigo')
ACTION = ('boss','chefe','vitoria','venci','ganhei','derrotei','consegui','morri',
          'matei','matar','atirando','tiro','explosao','explodiu','combate',
          'perseguicao','policia','fugir','fugi','correndo','pulei','batida',
          'colisao','luta','ataque','esquiva','escapei','salvei','missao')
COMMENTARY = ('eu acho','eu penso','eu pensei','eu tava','eu estava','eu vou',
              'eu queria','eu tentei','eu sinto','eu gostei','eu prefiro',
              'na minha opiniao','pra mim','para mim','eu acredito','eu sabia',
              'eu percebi','eu nao sei','eu nao consigo','deixa eu',
              'vou tentar','vou fazer','a gente','porque','por causa',
              'o problema e','faz sentido','sinceramente','na verdade',
              'nesse jogo','o jogo','eu lembro','to pensando','estou pensando',
              'quero ver','vamos ver','imagina se')
OBSERVATION = ('olha isso','olha so','olha aqui','olha ali','olhem',
               'repara','reparem','perceberam','voce viu','voces viram',
               'ta vendo','tao vendo','o que e isso','que isso','o que foi isso',
               'que coisa','que estranho','que bonito','que bizarro',
               'que interessante','esse detalhe','um detalhe','detalhe',
               'isso aqui','aquilo ali','esse lugar','essa parte',
               'nao tinha visto','nunca tinha visto','nunca vi',
               'descobri','descoberta','encontrei','segredo','easter egg',
               'presta atencao','observa','reparei','percebi')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def overlap(a,b):
    return any(max(x,u)<min(y,v) for x,y in a for u,v in b)


def _normalize(value):
    value=unicodedata.normalize('NFKD',value.casefold())
    value=''.join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r'\s+',' ',re.sub(r'[^\w\s]',' ',value)).strip()


def _find_cues(normalized_text,phrases):
    return [phrase for phrase in phrases if re.search(r'\b'+re.escape(phrase)+r'\b',normalized_text)]


def _clamp(value,limit=1):
    return max(0,min(limit,value))


def validate(data,duration):
    for c in data['clips']:
        if set(c['scores'])!=set(LIMITS):raise ValueError('Ranking deve conter os seis critérios.')
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=LIMITS[k] for k,v in c['scores'].items()):
            raise ValueError('Nota fora dos limites.')
        if c['score']!=sum(c['scores'].values()):raise ValueError('Total não corresponde aos critérios.')
        if c.get('category') is not None and c['category'] not in KINDS:
            raise ValueError('Categoria do corte inválida.')
        previous=-1
        for a,b in c['parts']:
            if not (math.isfinite(a) and math.isfinite(b) and 0<=a<b<=duration and a>=previous):
                raise ValueError('Intervalo inválido ou fora de ordem.')
            previous=b
        if not 30<=sum(b-a for a,b in c['parts'])<=60:raise ValueError('Corte deve durar de 30 a 60 segundos.')
    return data


def _starts(segments,duration,length):
    maximum=max(0,duration-length)
    starts=set(range(0,max(1,int(maximum)+1),15))
    starts.add(round(maximum,3))
    # Alinha o início com uma frase ou com um comentário que ocorre no meio.
    last_anchor=-100
    for s in segments:
        t=s['start']
        if t-last_anchor<8:continue
        last_anchor=t
        starts.add(round(_clamp(t-3,maximum),3))
        starts.add(round(_clamp(t-length*.43,maximum),3))
    return sorted(starts)


def _valid_segments(rows):
    return sorted((s for s in rows if s.get('start') is not None
                   and s.get('end') is not None and s['end']>s['start']
                   and s.get('avg_logprob',0)>-.9 and s.get('no_speech_prob',0)<.62
                   and s.get('text','').strip()),key=lambda s:s['start'])


def _candidate(start,length,segments,segment_starts,visual,visual_times,energy):
    end=start+length
    left=max(0,bisect.bisect_left(segment_starts,start)-2)
    right=bisect.bisect_left(segment_starts,end)
    spoken=[s for s in segments[left:right] if s['end']>start]
    first=bisect.bisect_left(visual_times,start)
    last=bisect.bisect_left(visual_times,end)
    frames=visual[first:last]
    ee=energy[int(start):math.ceil(end)]
    text=' '.join(s['text'].strip() for s in spoken)
    normalized=_normalize(text)
    reactions=_find_cues(normalized,REACTIONS)
    events=_find_cues(normalized,ACTION)
    comments=_find_cues(normalized,COMMENTARY)
    observations=_find_cues(normalized,OBSERVATION)
    words=re.findall(r'\w+',normalized)
    speech=_clamp(sum(max(0,min(end,s['end'])-max(start,s['start'])) for s in spoken)/length)
    movement=sum(v.get('difference',0) for v in frames)/max(1,len(frames))
    peak=max((v.get('difference',0) for v in frames),default=0)
    brightness=sum(v.get('brightness',0) for v in frames)/max(1,len(frames))
    sound=sum(ee)/max(1,len(ee))
    volume_peak=max(ee,default=0)
    if not (brightness>5 and (movement>1.5 or observations)):
        return None
    if not (reactions or events or comments or observations or
            (movement>=8 and sound>.004) or (movement>=14 and peak>=22)
            or (speech>=.20 and len(words)>=14)):
        return None

    visual_signal=_clamp((movement-1)/21)
    visual_peak=_clamp((peak-1)/32)
    sound_signal=_clamp(sound/.075)
    burst_signal=_clamp((volume_peak-max(.003,sound))/(max(.02,sound*2)))
    speech_signal=_clamp(speech/.52)
    words_signal=_clamp(len(words)/70)
    action_cues=_clamp(len(events)/2.5)
    comment_cues=_clamp(len(comments)/2)
    observation_cues=_clamp(len(observations)/1.8)
    reaction_cues=_clamp(len(reactions)/2)
    question_signal=1 if '?' in text else 0
    visual_ok=_clamp(brightness/55)
    action=round(34*visual_signal+19*visual_peak+14*sound_signal+
                 8*burst_signal+17*action_cues+8*reaction_cues)
    commentary=round(36*speech_signal+24*words_signal+23*comment_cues+
                     10*visual_signal+7*visual_ok)
    observation=round(37*observation_cues+19*speech_signal+16*question_signal+
                      12*words_signal+11*visual_signal+5*visual_ok)
    qualifies={
        'acao':(movement>=7 and sound>.003) or (movement>=14 and peak>=22)
               or (bool(events) and movement>=3),
        'comentario':speech>=.18 and len(words)>=12 and movement>=1.5,
        'observacao':bool(observations) and speech>=.06 and len(words)>=5,
    }
    categories={key:int(_clamp(value,100)) for key,value in
                {'acao':action,'comentario':commentary,'observacao':observation}.items()}
    eligible=[key for key in KINDS if qualifies[key] and categories[key]>=32]
    if not eligible:return None
    best=max(eligible,key=lambda key:categories[key])
    boundary_penalty=3 if spoken and (spoken[-1]['end']>end-.5 or spoken[0]['start']<start-1) else 0
    scores={
        'visual':round(_clamp(2+19*visual_signal+4*visual_peak,25)),
        'reacoes':round(_clamp(7*len(reactions)+3*len(observations)+2*len(events),25)),
        'entretenimento':round(_clamp(max(categories.values())*.17+2*reaction_cues,20)),
        'narrativa':round(_clamp(10*speech_signal+5*max(comment_cues,observation_cues)-boundary_penalty,15)),
        'qualidade':round(_clamp(4*visual_ok+3*sound_signal+(3 if .003<sound<.3 else 0),10)),
        'originalidade':3 if len(set(words))>=6 or events else 2,
    }
    score=sum(scores.values())
    quote=' '.join(text.split())[:145]
    reasons={
        'acao':f'Movimento {movement:.1f}, pico visual {peak:.1f}; sinais de ação: {", ".join(events[:2]) or "movimentação e som"}.',
        'comentario':f'Fala em {speech:.0%} do trecho, {len(words)} palavras; indícios de comentário: {", ".join(comments[:3]) or "fala contínua"}.',
        'observacao':f'Expressões de observação: {", ".join(observations[:3])}; fala em {speech:.0%} do trecho.',
    }
    titles={
        'acao':f'Ação: {events[0]}' if events else 'Momento de gameplay intenso',
        'comentario':'Comentando a gameplay',
        'observacao':f'Observando: {observations[0]}' if observations else 'Detalhe da gameplay',
    }
    return {
        'start':start,'end':end,'parts':[[start,end]],'score':score,'scores':scores,
        'title':titles[best],'hook':titles[best],
        'category':best,'category_scores':categories,'eligible_categories':eligible,
        'reason':reasons[best],'category_reasons':reasons,'quote':quote,
        'evidence':{
            'reaction_cues':reactions,'event_cues':events,'commentary_cues':comments,
            'observation_cues':observations,'movement_mean':round(movement,2),
            'movement_peak':round(peak,2),'brightness_mean':round(brightness,2),
            'audio_rms':round(sound,4),'audio_peak_rms':round(volume_peak,4),
            'speech_fraction':round(speech,2),'word_count':len(words),
            'sentence_boundary_penalty':boundary_penalty,
        },
        'tokens':sorted(set(re.findall(r'\w{4,}',normalized))),
    }


def _compatible(candidate,chosen):
    for other in chosen:
        if overlap(candidate['parts'],other['parts']) or abs(candidate['start']-other['start'])<65:
            return False
        a,b=set(candidate['tokens']),set(other['tokens'])
        if len(a)>=5 and len(b)>=5 and len(a&b)/max(1,len(a|b))>.70:
            return False
    return True


def _select(candidates,cfg):
    minimum=cfg['minimum_score']
    style=cfg.get('selection_style','balanced')
    if style not in STYLES:raise ValueError('Estilo de seleção inválido.')
    chosen=[]
    for desired in STYLES[style]:
        available=(c for c in candidates if c['score']>=minimum
                   and desired in c['eligible_categories'] and _compatible(c,chosen))
        best=max(available,key=lambda c:(c['category_scores'][desired],c['score']),default=None)
        if best:
            best['category']=desired
            best['reason']=best['category_reasons'][desired]
            if desired=='comentario':best['title']=best['hook']='Comentando a gameplay'
            elif desired=='observacao':best['title']=best['hook']='Observando a gameplay'
            elif desired=='acao':best['title']=best['hook']='Momento de ação'
            chosen.append(best)
    while len(chosen)<4:
        available=[c for c in candidates if c['score']>=minimum and c not in chosen
                   and _compatible(c,chosen)]
        if not available:break
        counts={kind:sum(x['category']==kind for x in chosen) for kind in KINDS}
        best=max(available,key=lambda c:(c['score']+.18*c['category_scores'][c['category']]
                    -9*counts[c['category']],c['score']))
        chosen.append(best)
    return chosen


def generate(folder,cfg,duration):
    segments=_valid_segments(read(folder/'transcript.json'))
    visual=sorted(read(folder/'visual.json'),key=lambda v:v['seconds_approx'])
    energy=read(folder/'energy.json')
    length=min(cfg['duration_seconds'],duration)
    if length<30:return {'method':'heuristic_v2_diverse','clips':[],'selected':[]}
    starts=[s['start'] for s in segments]
    visual_times=[v['seconds_approx'] for v in visual]
    candidates=[]
    for start in _starts(segments,duration,length):
        candidate=_candidate(start,length,segments,starts,visual,visual_times,energy)
        if candidate:candidates.append(candidate)
    candidates.sort(key=lambda c:(c['score'],max(c['category_scores'].values()),
                                  c['scores']['narrativa']),reverse=True)
    for index,candidate in enumerate(candidates,1):
        candidate['rank']=index
        candidate['slug']=f"{candidate['score']}pts_candidato_{index:03}"
        candidate['selected']=False
    selected=_select(candidates,cfg)
    for candidate in selected:candidate['selected']=True
    return {
        'method':'heuristic_v2_diverse',
        'warning':('Classificação por sinais, palavras e movimento — NÃO identifica com certeza '
                   'a voz do criador, a história, um boss ou acontecimentos visuais. '
                   'Os 4 Shorts devem ser revisados antes da publicação.'),
        'selection_style':cfg.get('selection_style','balanced'),
        'clips':candidates,
        'selected':[c['rank'] for c in selected],
        'composition':{kind:sum(c['category']==kind for c in selected) for kind in KINDS},
    }


def selected(data):
    chosen=set(data['selected'])
    return [c for c in data['clips'] if c['rank'] in chosen]
