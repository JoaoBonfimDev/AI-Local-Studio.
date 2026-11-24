# Verificação da versão 1.0

Executada em 21/11/2026 no Windows com Python 3.14, NumPy, FFmpeg 9.0.2 e NVIDIA GeForce RTX 4060 8 GB.

Resultado: **23 testes descobertos, 20 aprovados, 3 não executados**, sem falhas nos testes executados. A saída integral está em `test_run.txt`.

## Verificações executadas

- Seleção de até 10 episódios, duração de 600–900 segundos por episódio, ordem global crescente, ausência de sobreposição ou repetição de intervalos.
- Fontes curtas, fontes estáticas/silenciosas, quantidade insuficiente de material elegível e planos editados inválidos.
- Combinações de limites, durações e volume de material, incluindo 500 minutos simulados.
- Análise de uma gravação sintética real de 13 minutos em CPU e em NVDEC com `scale_cuda`.
- Renderização real de um episódio de 12 minutos com dois intervalos separados, em FFV1/CPU e em NVDEC + H.264 NVENC lossless.
- Comparação dos hashes de **todos** os quadros dos dois episódios com os quadros correspondentes da fonte, incluindo a ordem dos cortes.
- Comparação binária dos samples PCM de **ambas** as faixas de áudio, com taxas originais de 48 kHz e 44,1 kHz.
- Duração dos episódios, largura, altura, proporção, formato de pixels e número de canais/faixas de áudio.
- Corte com tempos fracionários, vídeo SDR de 10 bits, fonte sem áudio e fonte VFR com comparação da sequência e dos timestamps dos quadros.
- Cancelamento antes do subprocesso e validação de arquivos locais.
- Handlers reais da interface exercitados em memória: HTML/token, consulta de estado, recusa de origens externas/Host não local, recusa de chamadas sem token e validação de entrada.

## Verificações pendentes

- Três testes de conexão HTTP por socket não foram executados: o ambiente de desenvolvimento bloqueou acesso a sockets locais com WinError 10013. A interface também não pôde ser aberta pelo navegador de teste, que recebeu timeout. O fluxo visual completo e o seletor nativo precisam ser verificados no Windows sem essa restrição. Os handlers foram testados em memória; isso não substitui a verificação visual.
- PyTorch CUDA opcional não foi executado: PyTorch não estava instalado no Python de teste. CUDA via `scale_cuda`, NVDEC e NVENC foram executados na RTX 4060.
- Não foi usado vídeo de gameplay real do usuário. Os testes usam fontes sintéticas e validam preservação e regras mecânicas; não avaliam se a seleção subjetiva corresponde aos melhores momentos de um jogo.
- HDR PQ/HLG e metadados HDR especiais são recusados nesta versão, para não descartar metadados silenciosamente.
- Os códigos dos dois projetos de referência foram examinados após o fornecimento local dos ZIPs. O Highlights continua independente. Os originais foram incluídos intactos no pacote geral; a integridade é verificada separadamente por SHA-256.

## Reproduzir

No PowerShell, dentro desta pasta e depois da instalação:

```powershell
$env:RUN_MEDIA_TESTS = '1'
$env:RUN_GPU_TESTS = '1'
$env:RUN_HTTP_TESTS = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Sem GPU NVIDIA, não defina RUN_GPU_TESTS. Sem liberação de sockets locais, não defina RUN_HTTP_TESTS. A suíte padrão, sem essas variáveis, executa somente os testes leves e informa os demais como skipped. `TESTAR.cmd` ativa as três categorias.
