# AI Local Studio 2.0.2

Um único programa local para transformar gravações em **Shorts**, **gameplay editada** ou **episódios de Highlights**. Reutiliza o ranking do Shorts 1.1, os planejadores do Gameplay 0.3 e os conceitos de seleção, segurança e processamento sequencial do Highlights 1.0. O navegador controla um servidor Python em `127.0.0.1`.

**Atualização 2.0.2:** campo Nome do jogo, pastas e MP4s com nomes próprios, arquivos técnicos separados e seleção explícita de GPU/NVENC antes da renderização. Veja [ATUALIZAR_2_0_2.md](docs/ATUALIZAR_2_0_2.md). Mantenha ambiente virtual, modelos e cache ao atualizar.

## Começar no Windows

1. Extraia o ZIP para uma pasta nova e curta, como `E:\AI-Local-Studio`. Não extraia sobre a instalação antiga.
2. Tenha Python 3.13 ou 3.14 instalado com Python no PATH e Tcl/Tk. O núcleo foi testado com **Python 3.14.7**.
3. Dê dois cliques em **INSTALAR.cmd**. Ele cria `.venv`, tenta instalar wheels das dependências e verifica FFmpeg/FFprobe. Se os executáveis estiverem ausentes, baixa a distribuição gratuita por HTTPS para `tools/`.
4. Dê dois cliques em **INICIAR.cmd**. Mantenha a janela aberta. O navegador abre em `http://127.0.0.1:8765/`.
5. Selecione a gravação e a pasta de saída, informe o nome do jogo e escolha o modo e clique em **Analisar e selecionar momentos**.
6. Revise os tempos e as caixas de aprovação. Use **Prévia** para gerar uma amostra reproduzível de até 60 segundos, inclusive de MKV.
7. Clique em **Renderizar trechos aprovados**. Os resultados só são publicados como concluídos após validação completa.

O programa não precisa de Work, ChatGPT, Codex, conta, chave ou API paga. Instalação de pacotes e download explícito do modelo precisam de internet inicialmente. A análise, seleção, transcrição com modelo existente e exportação funcionam localmente. Nenhuma gravação é enviada. As fontes de download usadas pelo instalador são PyPI e a distribuição FFmpeg da Gyan; o download opcional do modelo usa Hugging Face/Systran.

## Os três modos

| Modo | Saída | Seleção e apresentação |
| --- | --- | --- |
| Shorts | Até 4 MP4, 1080 × 1920, 30–60 s | Ranking original de seis critérios, categorias ação/comentário/observação, diversidade temporal e textual. Tela inteira centralizada sobre fundo desfocado, como na composição anterior. Legendas opcionais. |
| Gameplay completa | Um MP4 horizontal, sem teto de duração | Remove somente longos períodos de baixa atividade e quase silêncio; mantém o vídeo inteiro se não houver remoção segura. |
| Gameplay melhores momentos | Um MP4 horizontal, sem teto de duração | Atividade audiovisual, evidências de fala e expressões, contexto antes/depois e ordem cronológica. |
| Highlights | 1–10 MP4 horizontais | Blocos relevantes ordenados cronologicamente; alvo padrão de 12 minutos, configurável inclusive acima de 15. Não repete intervalos nem acrescenta material apenas para preencher. |

Pouco conteúdo pode produzir menos de quatro Shorts ou menos episódios de Highlights. Um último episódio abaixo do alvo é identificado no plano e pode ser rejeitado. Os modos horizontais mantêm enquadramento, resolução de fontes com dimensões pares, proporção e áudio original; sem legendas, títulos, logos, músicas, zoom ou efeitos. Veja [MODOS.md](docs/MODOS.md).

## Transcrição e sua RTX 4060

O instalador tenta preparar Faster-Whisper/CTranslate2 usando somente wheels. Se faltar uma wheel para seu Python, ou a rede estiver indisponível, a edição audiovisual continua funcionando com **Transcrição desativada**. **INSTALAR_IA.cmd** repete a instalação sem alterar o Python global.

Em **Falas, legendas e análise avançada**, selecione a pasta de um modelo Faster-Whisper existente, contendo `model.bin`, ou clique em **Baixar modelo gratuito**. Comece com `small`, lote 1 e CUDA automática/FP16. Ative a transcrição. A interface admite idioma automático, VAD, INT8/FP16 e lotes 1–4 quando suportados pela instalação.

O mesmo modelo é utilizado por todos os modos; não há três modelos simultâneos. A transcrição roda em um processo separado, que termina e libera a VRAM antes da renderização. CUDA e NVENC são capacidades diferentes. Veja [GPU_CUDA.md](docs/GPU_CUDA.md).

## Exportação e áudio

Formato final padrão: **MP4, H.264, yuv420p, AAC-LC, faststart**. NVENC é testado com uma codificação real. A opção inicial GPU NVIDIA — NVENC exige a GPU. GPU preferencial · fallback CPU permite libx264 quando necessário; o painel informa o codificador real. Equilibrado, Alta qualidade e Ultra usam opções próprias para cada encoder.

O pipeline anterior de Highlights entregava FFV1/PCM em MKV. Esse caminho não é usado pela interface 2.0. Agora cada trecho é intermediado em NUT com H.264 e PCM; os timestamps e o comprimento do áudio são normalizados. A montagem copia o H.264 e codifica **uma única sequência AAC por episódio**, evitando reiniciar o encoder AAC em cada junção. Os intermediários PCM nunca são oferecidos como resultado final.

Cada final passa por FFprobe, conferência de codecs, dimensões, duração, início e duração de A/V, faststart, DTS monotônico, lacunas de pacotes de áudio e **decodificação integral**. Cada MP4 possui relatório de validação na área técnica `.studio/`, separado da pasta dos vídeos. Somente após isso o arquivo recebe seu nome final e aparece como concluído.

## Cache, interrupção e retomada

Análise, seleção e renderização são etapas separadas. O cache utiliza caminho, tamanho, mtime, amostras de conteúdo, versão do algoritmo e configurações de cada etapa. Trocar modo, destino, sensibilidade ou qualidade não invalida desnecessariamente áudio/movimento/transcrição. Trocar a amostragem visual só exige recalcular a análise visual; trocar modelo/faixa/idioma/VAD gera uma etapa de fala própria.

**Interromper** cancela o processo ativo. **Retomar** recupera os blocos concluídos; o bloco/corte incompleto é refeito. Após reiniciar o programa, use **Recuperar última sessão**, depois **Retomar**. Apenas a sessão mais recente possui recuperação automática pela interface. A fonte deve permanecer com a mesma identidade. Arquivos intermediários de uma operação interrompida ficam em `.render/` na pasta de saída e podem consumir espaço.

O percentual corresponde à **etapa atual**, medido por segundos efetivamente processados, checkpoints ou progresso estruturado do FFmpeg. Não há percentual global artificial. ETA refere-se à etapa e pode não estar disponível no começo ou ao carregar um modelo. CPU/RAM aparecem quando psutil está instalado; GPU/VRAM usam nvidia-smi quando disponível.

## Testes e estado real

As melhorias 2.0.2 têm relatório próprio em [VALIDACAO_2_0_2.md](docs/VALIDACAO_2_0_2.md), incluindo exportação com nomes, preservação de arquivo existente e escolha de NVENC sem reanálise.

A correção 2.0.1 e os testes com fonte full range nos três modos estão em [VALIDACAO_2_0_1.md](docs/VALIDACAO_2_0_1.md). O relatório VALIDACAO.md abaixo registra a validação inicial da versão 2.0.

Execute **TESTAR.cmd**. São usados somente vídeos e áudios sintéticos. A suíte exercita os três seletores, renderização CPU, GPU real quando disponível, quatro Shorts, múltiplos episódios, ausência de áudio, continuidade, sincronização flash/beep, cache, retomada e proteção local.

**Limites desta entrega:** Faster-Whisper/CTranslate2 não estavam instalados no Python acessível no ambiente de desenvolvimento; a transcrição real e a instalação online dessas wheels não foram validadas aqui. O servidor iniciou, mas as conexões ao localhost foram bloqueadas pelo ambiente (WinError 10013 e timeout do navegador). Os handlers HTTP foram testados em memória; o fluxo visual completo e os seletores nativos ainda exigem conferência no Windows fora desse ambiente. NVENC, NVDEC/scale CUDA e mídia CPU foram testados na RTX 4060 presente. Consulte [VALIDACAO.md](docs/VALIDACAO.md) para números e evidências.

Seleção é heurística, sem compreensão multimodal do jogo ou identificação segura do locutor. Não há diarização/separação de voz implementada. HDR e fontes com rotação são recusados para evitar alterações silenciosas. Fontes VFR são normalizadas para o FPS médio informado; fontes CFR preservam sua taxa racional. Dimensões ímpares recebem no máximo um pixel de padding, sem crop. O H.264/AAC é uma conversão com perdas mesmo em Ultra.

## Código e repositório

Para novos trabalhos, os MP4s ficam em `Saída/Nome do jogo/Modo/`, com nomes como `GTA 6 - Shorts 01.mp4`. Planos, relatórios e temporários ficam em `Saída/Nome do jogo/.studio/`. Nomes repetidos recebem `(2)` sem sobrescrever. Sessões antigas preservam seus destinos.

`core/` contém análise/cache/transcrição/GPU/jobs; `modes/` contém os seletores; `render/` faz exportação e validação; `web/` serve uma única interface. `legacy/` preserva os módulos anteriores para rastreabilidade e reutilização. Os antigos servidores/exportadores não são iniciados pela aplicação 2.0 e sua documentação em `docs/historico/` descreve versões antigas.

O ZIP não inclui modelos, vídeos, ambientes virtuais, ferramentas binárias ou caches. Nenhum push/merge foi realizado. Veja [GITHUB.md](docs/GITHUB.md) para atualizar o repositório existente na branch `dev/ai-local-studio-2.0`, preservando seu histórico.

Autor do projeto: João Victor Bonfim de Oliveira — [JoaoBonfimDev](https://github.com/JoaoBonfimDev).

Para verificar inferência de fala de verdade com um modelo existente, execute **TESTAR_IA.cmd**. O teste gera fala sintética offline e informa se CUDA ou CPU foi utilizado; não foi executado no ambiente desta entrega.
