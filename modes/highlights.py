"""Generalize Highlights 1.0's ranked blocks to arbitrary episode durations."""
import math
from core.ranking import enrich,protect_dialogue
from legacy.gameplay_editor.planner import merge_intervals


def select(analysis,segments,info,settings):
    scores=enrich(analysis,segments,speech_weight=settings['speech_weight'],cue_weight=settings['cue_weight'])
    block=settings['context_seconds']
    candidates=[]
    for start in range(0,math.ceil(info['duration']),block):
        end=min(info['duration'],start+block)
        a=analysis['audio'][start:math.ceil(end)];m=analysis['motion'][start:math.ceil(end)]
        score=sum(scores[start:math.ceil(end)])/max(1,len(a))
        # Keep the original absolute activity gate; silence/static footage is not padding.
        if (max(m,default=0)<.02 and max(a,default=0)<.01) or score<.12:continue
        candidates.append(dict(start=start,end=end,score=score))
    if not candidates:return []
    candidates.sort(key=lambda b:(-b['score'],b['start']))
    fraction=.25+.75*settings['sensitivity']/100
    budget=max(1,math.ceil(len(candidates)*fraction))
    selected=sorted(candidates[:budget],key=lambda b:b['start'])
    spans=protect_dialogue([(b['start'],b['end']) for b in selected],segments,info['duration'])
    target=settings['episode_minutes']*60
    maximum=settings['episodes']
    # Split only as needed, keeping chronological order across episode boundaries.
    episodes=[];current=[];seconds=0.
    for start,end in spans:
        while start<end-.01 and len(episodes)<maximum:
            remaining=target-seconds
            stop=min(end,start+remaining)
            # Avoid cutting a known sentence at an episode boundary, up to 12 s extension.
            if stop<end:
                for row in segments:
                    if row['start']<stop<row['end'] and row['end']-stop<=12:
                        stop=min(end,row['end']+.4)
            current.append(dict(start=start,end=stop,reason='Bloco relevante com contexto'))
            seconds+=stop-start;start=stop
            if seconds>=target-.01:
                episodes.append(dict(number=len(episodes)+1,segments=current));current=[];seconds=0.
    # A short last episode is explicit, never filled with duplicated/static material.
    if current and len(episodes)<maximum:
        episodes.append(dict(number=len(episodes)+1,segments=current))
    return episodes
