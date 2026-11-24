# AI Highlights Generator 1.0

Terceiro projeto independente para montar episódios cronológicos de melhores momentos de gameplay. Opera 100% local, sem APIs pagas e sem legendas, zoom, crop, efeitos ou mudanças de proporção.

Comece por **INSTALACAO_WINDOWS.md**. Execute **INSTALAR.cmd** uma vez e depois **INICIAR.cmd**.

- Até 10 episódios, cada um com 10–15 minutos, sem repetição de intervalos da fonte.
- Seleção por movimento/energia do áudio, com contexto de 60 segundos e revisão/edição dos tempos antes de renderizar.
- CUDA na redução para análise, NVDEC na decodificação e NVENC lossless quando o teste na fonte passar. Fallback FFV1 mantém os pixels sem perdas. Pontuação PyTorch CUDA opcional.
- Resolução, formato de pixels e cadência dos quadros mantidos; todas as faixas de áudio exportadas separadamente em PCM sem perdas de samples.
- A saída usa MKV e pode ser muito maior que o arquivo original. Metadados HDR especiais não suportados são recusados explicitamente.
- UI com progresso, cancelamento, plano JSON e pasta exclusiva por execução.

O nome “AI” não implica um modelo semântico: esta versão usa seleção heurística audiovisual. Ela não garante detectar todos os melhores momentos ou compreender a história do jogo. Não altera, importa nem depende dos outros projetos.

Estrutura: `main.py` inicia o servidor; `highlights/selection.py` analisa e seleciona; `highlights/media.py` controla codecs e render; `highlights/server.py` gerencia o trabalho e a API local; `web/index.html` contém a interface; `tests/` contém testes reproduzíveis.
