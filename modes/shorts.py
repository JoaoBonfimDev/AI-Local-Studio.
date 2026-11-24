"""Reuse the original six-criterion, category/diversity Shorts ranking."""
from legacy.aishorts.ranking import generate, selected
from core.process import save_json


def select(analysis, segments, info, settings, folder):
    save_json(folder/'transcript.json', segments)
    save_json(folder/'visual.json', analysis['visual'])
    save_json(folder/'energy.json', analysis['audio'])
    result=generate(folder,dict(duration_seconds=settings['short_seconds'], minimum_score=settings['minimum_score'], selection_style=settings['selection_style']),info['duration'])
    chosen=sorted(selected(result),key=lambda c:c['start'])
    return [dict(number=i+1,segments=[dict(start=a,end=b,reason=c['reason'],score=c['score'],category=c['category']) for a,b in c['parts']]) for i,c in enumerate(chosen)],result
