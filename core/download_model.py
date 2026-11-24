"""Only explicitly requested model downloads access the internet."""
from pathlib import Path
import sys

if __name__=='__main__':
    from huggingface_hub import snapshot_download
    model=sys.argv[1]
    if model not in {'tiny','base','small','medium'}:raise ValueError('Modelo inválido')
    snapshot_download('Systran/faster-whisper-'+model,local_dir=str(Path(sys.argv[2]).resolve()),
        allow_patterns=['model.bin','config.json','tokenizer.json','vocabulary.*','preprocessor_config.json'])
