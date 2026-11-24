"""Human-readable local names, safe on Windows and without path traversal."""
import re
import unicodedata
from pathlib import Path


def game_name(value, fallback='Gameplay'):
    if not isinstance(value,str):raise ValueError('Nome do jogo precisa ser texto.')
    text=unicodedata.normalize('NFC',value).strip()
    text=re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]',' ',text)
    text=re.sub(r'\s+',' ',text).strip(' .')
    text=text[:48].rstrip(' .')
    if not text:text=fallback
    if text.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        text='_'+text
    return text


def mode_folder(settings):
    if settings['mode']=='shorts':return 'Shorts'
    if settings['mode']=='highlights':return 'Highlights'
    return 'Gameplay - Melhores momentos' if settings['gameplay_mode']=='best' else 'Gameplay - Completa'


def video_stem(settings,number):
    name=game_name(settings['game_name'])
    if settings['mode']=='shorts':return f'{name} - Shorts {number:02}'
    if settings['mode']=='highlights':return f'{name} - Highlights - Episodio {number:02}'
    kind='Melhores momentos' if settings['gameplay_mode']=='best' else 'Completa'
    return f'{name} - Gameplay longa - {kind}'


def unique_video(directory,stem):
    directory=Path(directory)
    count=1
    while True:
        candidate=directory/(stem+('' if count==1 else f' ({count})')+'.mp4')
        if not candidate.exists():return candidate
        count+=1
