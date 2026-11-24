from legacy.gameplay_editor.planner import full_gameplay, best_moments
from core.ranking import enrich, protect_dialogue


def select(analysis, segments, info, settings):
    if settings['gameplay_mode']=='full':
        spans=full_gameplay(analysis['audio'],analysis['motion'],info['duration'],min_idle=settings['min_idle'])
    else:
        spans=best_moments(enrich(analysis,segments,speech_weight=settings['speech_weight'],cue_weight=settings['cue_weight']),info['duration'],sensitivity=settings['sensitivity'])
    spans=protect_dialogue(spans,segments,info['duration'])
    return [dict(number=1,segments=[dict(start=a,end=b,reason='Atividade e contexto; revisão recomendada') for a,b in spans])] if spans else []
