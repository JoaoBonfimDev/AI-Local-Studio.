# Atualização 2.0.2

Nome do jogo, pastas por modalidade, nomes descritivos dos MP4s, área técnica separada, GPU NVENC explícita com indicação do encoder real e escolha de encoder/qualidade na revisão sem reanalisar. Veja [ATUALIZAR_2_0_2.md](ATUALIZAR_2_0_2.md). A correção de cor 2.0.1 está mantida.

# Atualização 2.0.1

Correção de saída full range/yuvj420p nos três modos, conversão correta de níveis, diagnóstico detalhado de formato e invalidação apenas dos intermediários de renderização. Veja [ATUALIZAR_2_0_1.md](ATUALIZAR_2_0_1.md).

# AI Local Studio 2.0 — notas de versão

- Uma única interface e servidor local para os três modos, com um trabalho pesado por vez.
- Adaptação do scanner original para blocos pequenos, cancelamento e cache compartilhado por etapa.
- Ranking diversificado do Shorts preservado; planejadores completos/melhores do Gameplay reutilizados; seleção por blocos do Highlights generalizada.
- Separação entre análise, plano revisável e renderização; mudanças de modo reaproveitam dados compatíveis.
- Prévia local de até 60 segundos e streaming Range para resultados.
- Estado persistido, recuperação da última sessão e retomada por blocos/cortes completos.
- MP4 H.264/yuv420p/AAC-LC/faststart obrigatório; FFV1/PCM deixam de ser finais padrão.
- Áudio PCM intermediário, normalização temporal e uma codificação AAC por vídeo; sem música ou normalização de volume.
- Validação completa antes de publicar cada final: FFprobe, duração/dimensões/codecs, A/V, faststart, DTS e decodificação real.
- Perfis Equilibrado/Alta/Ultra e fallback CPU com parâmetros específicos de cada encoder.
- Modelos de fala isolados em processo separado; CUDA automática, VAD, precisão e lote configuráveis.
- Segurança local: 127.0.0.1, Host, Origin, token CSRF, caminhos locais, comandos sem shell e originais preservados.
- Instaladores CMD, ambiente virtual isolado, testes sintéticos e documentação de migração.

## Pendências transparentes

- Fluxo completo no navegador e seletor nativo não foram validados neste ambiente por bloqueio de localhost.
- Instalação online das wheels e transcrição real Faster-Whisper/CUDA não executadas aqui; exigem bibliotecas e modelo local.
- Seleção continua heurística, sem diarização ou reconhecimento visual semântico.
- VFR é normalizado para FPS médio; HDR/rotação são recusados; saídas compatíveis são 8 bits com compressão com perdas.
- A interface recupera automaticamente apenas a última sessão. Não há fila de vários trabalhos simultâneos nem editor gráfico de timeline por arraste.
- Sem avaliação subjetiva sobre uma gameplay real de várias horas nesta entrega.
