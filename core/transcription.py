"""Whisper runs in one separate process, freeing VRAM before rendering."""
import importlib.util
from pathlib import Path
import sys
from .cache import key
from .process import load_json


def transcribe(info, cache, runner, settings):
    if not settings.get('transcribe') or not info['audio']:
        return [], 'Desativada ou fonte sem áudio'
    if importlib.util.find_spec('faster_whisper') is None:
        raise ValueError('Faster-Whisper não está instalado neste Python. Execute INSTALAR_IA.cmd ou desative Transcrição para continuar com análise audiovisual.')
    model = Path(settings.get('model_path') or '').expanduser().resolve()
    if not (model/'model.bin').is_file():
        raise ValueError('Escolha a pasta de um modelo Faster-Whisper local ou use Baixar modelo na interface. Nenhum download é feito durante a análise.')
    model_stat = (model/'model.bin').stat()
    config = {k: settings[k] for k in ['language', 'audio_track', 'vad', 'compute_type', 'batch_size', 'transcription_device']}
    config.update(model_path=str(model), model_size=model_stat.st_size, model_mtime=model_stat.st_mtime_ns)
    folder = cache.stage('transcript', config)
    result = cache.get(folder/'complete.json')
    if result is None:
        runner.run([sys.executable, '-X', 'utf8', '-m', 'core.whisper_worker', info['path'], str(folder), __import__('json').dumps(config)],
            external_progress=folder/'progress.json')
        result = load_json(folder/'complete.json')
    else:
        runner.report('Transcrição em cache', info['duration'], info['duration'], 'Falas recuperadas sem executar o modelo')
    return result['segments'], result['device']
