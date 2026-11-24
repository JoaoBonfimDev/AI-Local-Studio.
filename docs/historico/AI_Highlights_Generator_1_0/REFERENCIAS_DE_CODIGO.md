# Referências de código e independência

Foram examinados os ZIPs `AI_Shorts_Generator_Local_Studio_1_1.zip` e `AI_Gameplay_Editor_Alpha_0_3.zip` fornecidos localmente pelo usuário. Nenhum arquivo desses dois projetos foi editado.

| Referência examinada | Uso como referência no Highlights |
| --- | --- |
| Shorts: `aishorts/ranking.py`, funções `overlap`, `_compatible`, `validate`, `_select` | Separar pontuação da seleção e validar intervalos antes de renderizar. O Highlights exige ausência de sobreposição global entre todos os episódios e seleciona até dez episódios longos, em vez de quatro Shorts. |
| Shorts: `aishorts/media.py` e configuração/README | FFmpeg local, separação entre análise e exportação, gravação do plano para revisão e manutenção de arquivos pessoais fora do pacote. O Highlights usa FFmpeg/FFprobe do PATH e NumPy; não depende do ambiente Whisper do Shorts. |
| Gameplay: `gameplay_editor/media.py`, `probe`, `scan_audio`, `scan_motion`, `_cuda_decodes`, `build_activity` | Análise de movimento e energia sonora com memória limitada, decodificação GPU realmente testada e fallback CPU. O Highlights acrescenta redução CUDA da cópia de análise e pontuação PyTorch CUDA opcional. |
| Gameplay: `gameplay_editor/planner.py`, `merge_intervals`, `best_moments`, `validate_timeline` | Ordem cronológica, reunião de intervalos adjacentes e revisão de tempos. O novo planejador usa blocos de contexto de 60 s, limites de 10–15 minutos por episódio e validação global de não repetição. |
| Gameplay: `gameplay_editor/render.py`, `render_timeline`, `_source_matches` | Cortes precisos, temporários sequenciais, proteção da fonte, verificação de fonte alterada e publicação de arquivos somente após validação. |

## Escolhas próprias para preservar o material

O renderizador original do Gameplay exporta MP4 H.264/AAC com FPS constante e parâmetros de áudio fixos; o Shorts tem composição vertical e legendas. Esses comportamentos continuam intactos nos respectivos projetos, mas não foram transferidos ao Highlights.

O Highlights exporta MKV com NVENC lossless compatível ou FFV1, preserva o formato de pixels e a cadência dos quadros, e mantém todas as faixas de áudio separadas em PCM. Testa a igualdade de pixels numa amostra antes de habilitar o caminho GPU de renderização. Não compartilha arquivos de configuração, caches, modelos, ambientes ou imports com os outros projetos.

Esta implementação não incorpora um modelo semântico: a qualidade editorial permanece dependente dos sinais de movimento/áudio e da revisão do usuário. Não foi adicionada dependência de API, login ou serviço pago.
