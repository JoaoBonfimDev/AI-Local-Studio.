# Instalação no Windows

1. Extraia o ZIP inteiro para uma pasta sua, por exemplo `E:\Projetos\AI_Studio`.
2. Abra a pasta `AI_Highlights_Generator_1_0`. Os outros projetos usam seus próprios ambientes e arquivos de inicialização.
3. Instale Python 3.12 ou mais recente de https://www.python.org/downloads/windows/ com a opção de adicionar ao PATH. Esta versão foi desenvolvida com Python 3.14. Não reutilize o ambiente virtual do Shorts ou do Gameplay Editor.
4. Instale uma distribuição completa do FFmpeg com FFprobe e suporte NVIDIA. A página https://ffmpeg.org/download.html aponta para builds Windows. Uma alternativa pelo terminal é `winget install --id Gyan.FFmpeg --exact`. Feche e reabra o terminal após a instalação. Os executáveis precisam estar no PATH.
5. Atualize o driver NVIDIA pelo NVIDIA App ou https://www.nvidia.com/Download/index.aspx . Não é necessário instalar o CUDA Toolkit para os recursos NVDEC, scale_cuda e NVENC usados pelo FFmpeg.
6. Execute `INSTALAR.cmd`. Ele cria somente `.venv` nesta pasta e instala NumPy. A instalação inicial exige internet; a operação depois disso é local.
7. Execute `INICIAR.cmd`. O navegador abrirá em http://127.0.0.1:8767 . Mantenha o terminal aberto.

## Uso

Selecione o vídeo e uma pasta com espaço livre. Não é preciso enviar/uploadar a gameplay. Escolha o máximo de episódios, a duração alvo e a proporção de material elegível. Clique em **Analisar e montar plano**. Revise os tempos na tabela. Se necessário, edite os segundos em **Editar os tempos do plano** e depois clique em **Renderizar episódios**. Um plano inválido é recusado antes de iniciar.

O alvo pode ser 11–14 minutos para deixar margem nos limites de 10–15. Quando há apenas 10 minutos elegíveis, é permitido um episódio de 10 minutos. O programa não repete nem estica vídeos para atingir a quantidade escolhida. Os trechos e os episódios seguem a ordem da gravação original, inclusive entre episódios.

Cada execução cria uma pasta exclusiva contendo `plano.json`, `plano_render.json`, `resultado.json` e `episodio_01.mkv` etc. Os planos usam segundos relativos ao início da gravação. Alterar o plano JSON no navegador não altera o vídeo original. Para outra análise, use novamente o primeiro botão. Se recarregar a página durante a análise, o progresso é recuperado enquanto o servidor estiver aberto. O plano não é retomado automaticamente após fechar o servidor; o JSON permanece disponível para consulta.

## GPU

Em **GPU automática**, o programa tenta NVDEC para decodificar, `scale_cuda` para reduzir exclusivamente a cópia de análise e, opcionalmente, PyTorch CUDA para calcular diferenças de quadros. Sem PyTorch, a pontuação usa NumPy; os caminhos CUDA/NVDEC/NVENC do FFmpeg continuam disponíveis.

Para habilitar também a pontuação PyTorch CUDA, visite https://pytorch.org/get-started/locally/ e use o comando indicado para Windows, Pip e uma versão CUDA compatível com seu driver dentro desta `.venv`. Ative o ambiente no PowerShell com `.\.venv\Scripts\Activate.ps1`, ou substitua `pip` por `.\.venv\Scripts\python.exe -m pip` no comando oficial. Não instale uma distribuição CPU esperando usar CUDA. Verifique com:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"
```

Na renderização, NVENC é usado somente se o formato for compatível e uma amostra da fonte mantiver os mesmos hashes de pixels decodificados. Se falhar, o programa usa FFV1 sem perdas na CPU; NVDEC pode continuar ativo. NVENC, CUDA de cálculo e NVDEC são recursos distintos, e o log mostra o caminho usado. Não há promessa de GPU 100% ocupada ou de ganho em todo vídeo. Um driver/build incompatível usa fallback sem reduzir qualidade.

## Preservação e espaço

A saída é MKV com vídeo sem perdas em relação aos pixels decodificados da fonte. Resolução, proporção, formato de pixels, tags de cor reconhecidas e timestamps dos quadros são mantidos. Não há `-r`, conversão para FPS fixo nem filtros que alterem a aparência. Na saída NVDEC, um estágio de formato nas mesmas dimensões desempacota NV12/P010 para o formato original; a amostra de pixels também é comparada antes de habilitar NVDEC na renderização. Vídeos VFR mantêm o espaçamento de seus quadros em cada trecho, com timestamps ajustados para concatenar os cortes. FPS médio do episódio VFR pode diferir da média de toda a fonte por selecionar uma parte diferente da gravação.

Todas as faixas de áudio são mantidas separadas, com canais e taxa de amostragem originais e sem normalização. São decodificadas para PCM no formato adequado à fonte: os samples são mantidos, mas o codec e o bitrate do arquivo mudam. Não há uma cópia binária do contêiner original; cortes precisos exigem uma nova codificação. O arquivo não precisa ter o mesmo tamanho do original. Vídeos sem perdas podem ocupar dezenas ou centenas de GB; a renderização mantém temporariamente os trechos de um episódio e a junção, podendo exigir cerca de duas vezes o tamanho desse episódio. O programa não estima com precisão o tamanho antes de renderizar. Os temporários de análise usam aproximadamente 104 MB/h de vídeo + 115 MB/h de áudio no disco temporário, com memória limitada por blocos de 1 minuto.

Use VLC ou mpv para reproduzir os MKVs. O navegador não precisa conseguir reproduzir o codec: a interface serve para configurar, acompanhar e revisar os tempos. Não há preview embutido nesta versão.

## Limites da versão 1.0

- A seleção é heurística audiovisual, sem modelo que compreenda combate, narrativa, fala ou o nome do jogo. Energia de música/câmera pode pontuar alto; uma cena importante e calma pode pontuar baixo. Revisão humana é recomendada.
- Analisa a primeira faixa de áudio para pontuação; exporta todas. Não usa Whisper e não cria legendas.
- Blocos de 60 segundos fornecem contexto, mas um corte pode interromper uma fala ou cena. A versão 1.0 não detecta fronteiras narrativas. A sobra final menor que 60 segundos não entra na seleção automática; pode ser incluída editando o plano.
- Fontes com menos de 10 minutos elegíveis não geram episódios. A quantidade é um teto de até 10.
- Apenas uma faixa de vídeo é suportada. Rotação não nula, HDR PQ/HLG e metadados HDR especiais detectados (Dolby Vision, mastering display, content light, HDR dinâmico) são recusados para não descartá-los silenciosamente. Não é uma solução de preservação de Dolby Vision/HDR10+.
- Formatos de pixels ou codecs PCM não suportados pelo FFmpeg/Matroska causam erro explícito, sem conversão silenciosa para um formato de menor qualidade.
- Sem exportação MP4 com perdas na versão 1.0; sem alterações nos outros dois programas.
- Cancelar remove os temporários da operação. Episódios já finalizados permanecem na saída. Não há retomada de render interrompido; inicie uma nova análise para uma nova pasta de execução.

## Diagnóstico e testes

```powershell
ffmpeg -version
ffprobe -version
nvidia-smi
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para integração completa, execute `TESTAR.cmd`. Ele gera uma gravação sintética pequena de 13 minutos, testa seleção, renderiza um episódio real de 12 minutos em CPU e GPU, compara pixels e samples de áudio, verifica ordem/duração e testa HTTP local. Não usa suas gravações. Sem NVIDIA, os testes de GPU devem ser desabilitados: remova `set RUN_GPU_TESTS=1` ou execute somente com `RUN_MEDIA_TESTS=1`. Leia também `TESTES.md` para o resultado do ambiente de desenvolvimento.

Porta ocupada: `.\.venv\Scripts\python.exe main.py --port 8768`. O servidor escuta apenas em `127.0.0.1`; não abra portas no roteador. Se o seletor não abrir, cole o caminho completo nos campos. Se um ambiente bloquear sockets locais, use o terminal normal do Windows para iniciar e testar.

## Referências técnicas

- NVIDIA/FFmpeg: https://docs.nvidia.com/video-technologies/video-codec-sdk/13.1/ffmpeg-with-nvidia-gpu/
- FFmpeg, `-fps_mode`, `-pix_fmt +` e mapeamento de streams: https://ffmpeg.org/ffmpeg.html
- Instalação CUDA opcional do PyTorch: https://pytorch.org/get-started/locally/
