"""Add speech/cue evidence to the existing audiovisual activity ranking."""
import math
from legacy.aishorts.ranking import _normalize, _find_cues, REACTIONS, ACTION, COMMENTARY, OBSERVATION
from legacy.gameplay_editor.planner import merge_intervals


def enrich(analysis, segments, *, speech_weight=.15, cue_weight=.15):
    activity=list(analysis['activity'])
    speech=[0.]*len(activity)
    cue=[0.]*len(activity)
    for row in segments:
        if row.get('avg_logprob',0)<-.9 or row.get('no_speech_prob',0)>.62: continue
        text=_normalize(row['text'])
        relevance=min(1.,len(_find_cues(text,REACTIONS+ACTION+COMMENTARY+OBSERVATION))/2)
        for i in range(max(0,int(row['start'])),min(len(activity),math.ceil(row['end']))):
            speech[i]=1.;cue[i]=max(cue[i],relevance)
    for i in range(len(activity)):
        activity[i]=min(1.,activity[i]*(1-speech_weight-cue_weight)+speech_weight*speech[i]+cue_weight*cue[i])
    return activity


def protect_dialogue(spans, segments, duration, max_extension=12):
    protected=[]
    for start,end in spans:
        for row in segments:
            if row.get('avg_logprob',0)<-.9 or row.get('no_speech_prob',0)>.62:continue
            if row['start']<start<row['end'] and start-row['start']<=max_extension:
                start=max(0,row['start']-.4)
            if row['start']<end<row['end'] and row['end']-end<=max_extension:
                end=min(duration,row['end']+.6)
        protected.append((start,end))
    return merge_intervals(protected)
