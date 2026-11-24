import math
from core.process import save_json
from . import shorts,gameplay,highlights


def validate(plan,duration,mode):
    episodes=plan.get('episodes')
    maximum=4 if mode=='shorts' else 10 if mode=='highlights' else 1
    if not isinstance(episodes,list) or not 1<=len(episodes)<=maximum:raise ValueError('Plano sem saídas ou com quantidade inválida.')
    previous=0.
    count=0
    for i,episode in enumerate(episodes,1):
        if not isinstance(episode,dict) or not isinstance(episode.get('segments'),list) or not episode['segments']:raise ValueError('Episódio vazio: remova o episódio ou aprove um trecho.')
        seconds=0.
        for row in episode['segments']:
            a,b=float(row['start']),float(row['end'])
            if not all(map(math.isfinite,(a,b))) or a<previous-1e-6 or a<0 or b<=a or b>duration+1e-6:
                raise ValueError('Trecho inválido, repetido, sobreposto ou fora de ordem.')
            previous=b;seconds+=b-a;count+=1
            row.update(start=a,end=b)
        if mode=='shorts' and not 30<=seconds<=60:raise ValueError('Cada Short precisa durar de 30 a 60 segundos.')
        episode.update(number=i,duration=seconds)
    if count>10000:raise ValueError('Plano excede 10.000 trechos; divida a operação.')
    return plan


def create(analysis,segments,info,settings,folder):
    mode=settings['mode'];details={}
    if mode=='shorts':episodes,details=shorts.select(analysis,segments,info,settings,folder)
    elif mode=='gameplay':episodes=gameplay.select(analysis,segments,info,settings)
    else:episodes=highlights.select(analysis,segments,info,settings)
    if not episodes:raise ValueError('Nenhum trecho atingiu os critérios. Ajuste a sensibilidade/nota ou escolha outra gravação. Nenhum preenchimento foi criado.')
    plan=validate(dict(version='2.0',mode=mode,episodes=episodes),info['duration'],mode)
    plan['note']='Seleção heurística. Fala do jogo e do criador pode estar misturada. Revise os intervalos.'
    if mode=='shorts' and len(episodes)<4:plan['note']+=f' Foram encontrados {len(episodes)} de 4 Shorts sem repetição.'
    if mode=='highlights' and episodes[-1]['duration']<settings['episode_minutes']*60:plan['note']+=' O último episódio é menor que o alvo por falta de material selecionado; pode ser rejeitado na revisão.'
    save_json(folder/'ranking.json',details)
    save_json(folder/'plano.json',plan)
    return plan
