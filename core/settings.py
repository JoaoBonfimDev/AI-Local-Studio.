import math

DEFAULTS=dict(game_name='',mode='shorts',gameplay_mode='full',episodes=10,episode_minutes=12.,short_seconds=45,
    sensitivity=60,minimum_score=35,selection_style='balanced',quality='high',encoder='nvenc',
    sample_seconds=2,context_seconds=30,min_idle=20.,transcribe=False,model_path='',language='',
    transcription_device='auto',compute_type='float16',batch_size=1,vad=True,captions=False,
    audio_track=0,render_audio_track=0,speech_weight=.15,cue_weight=.15)


def validate(data):
    result=dict(DEFAULTS)
    result.update({k:v for k,v in data.items() if k in DEFAULTS})
    from .naming import game_name
    if not isinstance(result['game_name'],str):raise ValueError('Nome do jogo precisa ser texto.')
    result['game_name']=game_name(result['game_name']) if result['game_name'].strip() else ''
    choices=dict(mode=['shorts','gameplay','highlights'],gameplay_mode=['full','best'],quality=['balanced','high','ultra'],
        encoder=['auto','cpu','nvenc'],selection_style=['balanced','action','commentary','observation'],
        transcription_device=['auto','cpu','cuda'],compute_type=['float16','int8_float16'],language=['','pt','en','es'])
    for name,allowed in choices.items():
        if result[name] not in allowed:raise ValueError('Configuração inválida: '+name)
    limits=dict(episodes=(1,10),episode_minutes=(.1,1440),short_seconds=(30,60),sensitivity=(0,100),minimum_score=(0,100),
        sample_seconds=(1,10),context_seconds=(10,120),min_idle=(1,3600),batch_size=(1,4),audio_track=(0,63),render_audio_track=(0,63),speech_weight=(0,.4),cue_weight=(0,.4))
    floating={'episode_minutes','min_idle','speech_weight','cue_weight'}
    for name,(low,high) in limits.items():
        number=float(result[name])
        if not math.isfinite(number) or not low<=number<=high or (name not in floating and not number.is_integer()):raise ValueError('Valor fora dos limites: '+name)
        result[name]=number if name in floating else int(number)
    for name in ['transcribe','vad','captions']:
        if not isinstance(result[name],bool):raise ValueError('Configuração booleana inválida: '+name)
    if not isinstance(result['model_path'],str):raise ValueError('Pasta de modelo inválida.')
    if result['captions'] and (result['mode']!='shorts' or not result['transcribe']):raise ValueError('Legendas exigem modo Shorts e transcrição ativada.')
    return result
