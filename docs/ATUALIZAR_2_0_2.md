# Atualização 2.0.2 — GPU explícita e organização por jogo

## Aplicar na instalação atual

1. Interrompa o trabalho e feche a janela do servidor do Studio.
2. Extraia o novo ZIP e copie o conteúdo de `AI-Local-Studio` para sua instalação, substituindo os arquivos do programa.
3. Mantenha `.venv`, `.local`, `tools`, modelos e vídeos de saída. Não precisa reinstalar dependências para estas melhorias.
4. Abra INICIAR.cmd e confira **2.0.2** no cabeçalho. Se necessário, atualize a página com Ctrl+F5.

As sessões antigas continuam recuperáveis, com seus destinos anteriores. Para usar a nova organização por jogo, inicie uma nova análise e preencha o nome. Se for o mesmo arquivo, os dados compatíveis da análise serão encontrados no cache. O Studio não move nem renomeia exportações antigas automaticamente.

## Nome do jogo e pastas

O novo campo **Nome do jogo** define os nomes de pastas e arquivos. É opcional: vazio usa o nome da gravação. Nomes são ajustados para caracteres válidos no Windows e limitados a 48 caracteres para reduzir problemas com caminhos longos. Não tentamos identificar o jogo por IA.

Exemplo: pasta de saída `E:\Videos`, nome `GTA 6`.

| Modo | Pasta dos vídeos | Nome de exemplo |
| --- | --- | --- |
| Shorts | `E:\Videos\GTA 6\Shorts` | `GTA 6 - Shorts 01.mp4` |
| Gameplay completa | `E:\Videos\GTA 6\Gameplay - Completa` | `GTA 6 - Gameplay longa - Completa.mp4` |
| Gameplay melhores momentos | `E:\Videos\GTA 6\Gameplay - Melhores momentos` | `GTA 6 - Gameplay longa - Melhores momentos.mp4` |
| Highlights | `E:\Videos\GTA 6\Highlights` | `GTA 6 - Highlights - Episodio 01.mp4` |

Os vídeos finais ficam separados dos planos, transcrições, relatórios de validação, prévias e intermediários. Esses arquivos técnicos ficam em `E:\Videos\GTA 6\.studio\<sessão>`. Os identificadores técnicos continuam existindo internamente para permitir cancelamento/retomada e impedir colisões, mas não aparecem nos nomes dos MP4s.

Se um vídeo com o mesmo nome já existir, o Studio cria `(2)`, `(3)` etc.; não sobrescreve. Ao retomar a mesma renderização, o destino registrado é reutilizado e validado em vez de criar uma cópia desnecessária. **Abrir pasta de saída** abre a pasta dos MP4s, não a pasta técnica.

## Renderizar na GPU

**GPU NVIDIA — NVENC** é a opção inicial. Ela testa NVENC de verdade e exige a codificação H.264 na GPU. Se NVENC falhar, mostra erro e não troca silenciosamente para CPU.

**GPU preferencial · fallback CPU** tenta NVENC e permite libx264 quando necessário. **CPU — libx264** permanece disponível. O painel mostra o codificador real confirmado: `GPU NVIDIA · NVENC` ou `CPU · libx264`, inclusive após fallback automático.

Na revisão, é possível escolher GPU/CPU e qualidade antes de clicar em Renderizar, sem refazer a análise. A nova escolha altera só o trabalho de renderização.

Codificação por GPU não significa que todas as etapas utilizem GPU: a composição vertical dos Shorts, conversão de faixa de cor, áudio, montagem e validação podem continuar na CPU. A redução/decodificação de análise usa NVDEC/CUDA quando compatível. O controle **GPU NVIDIA — NVENC** garante o encoder, sem prometer 100% de processamento CUDA ou um percentual específico de ocupação da placa.

## Compatibilidade

A correção full range/yuvj420p da 2.0.1 está mantida nos três modos. Os finais continuam MP4/H.264/yuv420p/AAC-LC/faststart, com decodificação integral e demais validações antes de exibir sucesso. A interface mantém o visual anterior, acrescentando somente os campos e indicadores relacionados a estas melhorias.
