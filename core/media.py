import math
import os
from pathlib import Path
import shutil
import json

from .process import Runner

ROOT = Path(__file__).resolve().parents[1]


def binary(name):
    local = ROOT / 'tools' / (name + ('.exe' if os.name == 'nt' else ''))
    found = str(local) if local.is_file() else shutil.which(name)
    if not found:
        raise RuntimeError(f'{name} ausente. Execute INSTALAR.cmd ou coloque os executáveis em tools/.')
    return found


def ffmpeg():
    return [binary('ffmpeg'), '-hide_banner', '-loglevel', 'error', '-xerror', '-nostdin', '-y']


def local_path(value, *, file=False):
    if not isinstance(value, str) or not value.strip() or '://' in value or '\x00' in value:
        raise ValueError('Informe um caminho local válido.')
    raw = value.strip().strip('"')
    # Reject UNC/device/network paths and NTFS alternate streams.
    if raw.startswith(('\\\\', '//')) or (os.name == 'nt' and ':' in raw[2:]):
        raise ValueError('Use um disco local, sem caminhos de rede ou fluxos alternativos.')
    path = Path(raw).expanduser().resolve()
    if str(path).startswith(('\\\\','//')):
        raise ValueError('O caminho resolvido precisa estar em um disco local.')
    if file and (not path.is_file() or path.suffix.lower() not in {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.ts'}):
        raise ValueError('Selecione um vídeo local existente.')
    return path


def probe(path, runner=None):
    runner = runner or Runner()
    data = json.loads(runner.run([binary('ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], timeout=60))
    videos = [s for s in data.get('streams', []) if s.get('codec_type') == 'video' and not s.get('disposition', {}).get('attached_pic')]
    if len(videos) != 1:
        raise ValueError('É necessária uma única faixa de vídeo.')
    v = videos[0]
    duration = float(data.get('format', {}).get('duration') or v.get('duration') or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('Duração inválida ou arquivo ainda não finalizado.')
    if v.get('color_transfer') in {'smpte2084', 'arib-std-b67'} or any('dovi' in str(s).lower() for s in v.get('side_data_list', [])):
        raise ValueError('HDR detectado. Esta versão exige SDR para exportar H.264 8 bits sem alterar as cores silenciosamente.')
    if any(float(s.get('rotation', 0)) != 0 for s in v.get('side_data_list', [])):
        raise ValueError('Fonte com rotação não suportada nesta versão.')
    stat = Path(path).stat()
    fps = v.get('avg_frame_rate') or v.get('r_frame_rate') or '30/1'
    if fps in {'0/0', '0/1'}: fps = '30/1'
    return dict(path=str(Path(path).resolve()), duration=duration, width=int(v['width']), height=int(v['height']), fps=fps,
        video=v, audio=[s for s in data['streams'] if s.get('codec_type') == 'audio'], size=stat.st_size, mtime_ns=stat.st_mtime_ns)
