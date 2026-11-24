"""Probe actual encoder operation; compiled FFmpeg support is insufficient."""
import ctypes
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from .media import ffmpeg
from .process import Runner

_DLL_HANDLES=[]


def configure_cuda():
    if os.name!='nt':return
    roots=[]
    for name in ['CUDA_PATH','CUDA_PATH_V12_9','CUDNN_PATH']:
        if os.environ.get(name):roots.extend([Path(os.environ[name])/'bin',Path(os.environ[name])])
    import sysconfig
    packages=Path(sysconfig.get_paths()['purelib'])/'nvidia'
    if packages.is_dir():roots.extend(packages.glob('*/bin'))
    for root in roots:
        if root.is_dir():
            try:_DLL_HANDLES.append(os.add_dll_directory(str(root)))
            except OSError:pass


def nvenc_available(runner=None):
    try:
        (runner or Runner()).run(ffmpeg() + ['-f', 'lavfi', '-i', 'color=s=640x360:r=30', '-frames:v', '2', '-c:v', 'h264_nvenc', '-pix_fmt', 'yuv420p', '-f', 'null', '-'], timeout=20)
        return True
    except (RuntimeError, OSError):
        return False


def telemetry():
    result = {'cpu_percent': None, 'ram_percent': None, 'gpu_percent': None, 'vram_mb': None, 'gpu_name': None}
    try:
        import psutil
        result.update(cpu_percent=psutil.cpu_percent(), ram_percent=psutil.virtual_memory().percent)
    except ImportError:
        pass
    if shutil.which('nvidia-smi'):
        try:
            p = subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=3, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if p.returncode == 0:
                name, use, memory = p.stdout.splitlines()[0].rsplit(',', 2)
                result.update(gpu_name=name.strip(), gpu_percent=float(use), vram_mb=float(memory))
        except (ValueError, OSError, subprocess.TimeoutExpired):
            pass
    return result


def diagnose():
    configure_cuda()
    libraries = {}
    for name in ['cublas64_12.dll', 'cudnn64_9.dll']:
        try:
            ctypes.CDLL(name); libraries[name] = True
        except OSError:
            libraries[name] = False
    devices = None
    error = None
    try:
        import ctranslate2
        devices = ctranslate2.get_cuda_device_count()
    except (ImportError, RuntimeError, OSError) as exc:
        error = str(exc)
    return dict(telemetry=telemetry(), nvenc=nvenc_available(), cuda_libraries=libraries,
        ctranslate2_cuda_devices=devices, whisper_installed=importlib.util.find_spec('faster_whisper') is not None, whisper_error=error,
        note='NVENC é testado por codificação real. CUDA Whisper só é confirmado ao transcrever com um modelo local.')
