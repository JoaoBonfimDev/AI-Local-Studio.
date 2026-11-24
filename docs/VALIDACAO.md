# Relatório de validação — AI Local Studio 2.0

Data de referência: 22/11/2026, horário de São Paulo. Execução do host atravessou 23/11 UTC.

## Resultado

**55 testes aprovados e 1 teste HTTP por socket não executado por bloqueio do ambiente.** Não há falhas na execução final. A suíte integrada foi executada dentro de uma `.venv` nova, sem depender de numpy, OpenCV, PyAV, Faster-Whisper ou pacotes instalados globalmente. O núcleo de mídia usa a biblioteca padrão e FFmpeg/FFprobe.

| Suíte | Aprovados | Não executados |
| --- | --- | --- |
| Studio 2.0, instalação isolada, 26 testes, 69,169 s | 25 | 1: conexão HTTP localhost, WinError 10013 |
| Shorts original, `test_core.py` | 9 | 0 |
| Gameplay original, `test_planner.py` | 8 | 0 |
| Gameplay original, `test_gpu_progress.py` | 5 | 0 |
| Highlights original, `test_selection.py` | 8 | 0 |
| Total | **55** | **1** |

As suítes originais de planejamento foram rodadas nas cópias de origem, antes de alterações nos códigos preservados. Elas documentam a base reaproveitada, não substituem os testes integrados novos. As suítes antigas completas de UI/renderização não foram todas repetidas: caminhos de exportação antigos são históricos e não são usados pelo Studio 2.0.

## Ambiente confirmado

- Windows, Python **3.14.7**; FFmpeg/FFprobe **9.0.2**, distribuição Gyan.
- GPU observada por nvidia-smi: **NVIDIA GeForce RTX 4060, 8.188 MiB**, driver 616.64.
- NVENC confirmado por codificação real e MP4 final validado.
- NVDEC + `scale_cuda` confirmados em análise de mídia sintética real.
- cuBLAS 12 foi localizado após incluir CUDA_PATH na procura de DLLs; cuDNN 9 não foi localizado neste Python.
- Faster-Whisper/CTranslate2 e psutil não estavam instalados no Python acessível. Não foi executada transcrição de inferência real nesta entrega.
- `scripts/setup_windows.py --offline` criou `.venv`, verificou ferramentas presentes e compilou módulos com sucesso. Não foi testado download online de dependências/FFmpeg nesta execução.
- JavaScript passou por `node --check`; Python passou por compileall.

## Matriz dos requisitos de teste

| Requisito | Evidência/estado |
| --- | --- |
| 1. Importação de vídeo | MP4/MKV sintéticos, nomes com espaços e FFprobe real |
| 2. Servidor local | Inicia em 127.0.0.1; handlers exercitados em memória. Conexão real/browsing bloqueados |
| 3. Escolher três modos | Seletores reais e Manager, com planos validados para Shorts/Gameplay/Highlights |
| 4. Análise audiovisual | FFmpeg real, áudio RMS e diferença/brightness de frames em blocos |
| 5. Cache | Segunda análise não pode chamar subprocesso; cache compartilhado entre modos e invalidação apenas visual |
| 6. Cronologia | Validação estrita de todos os intervalos, inclusive entre episódios |
| 7. Não repetição | Sobreposição/repetição recusadas e seleção cronológica disjunta |
| 8. Proporção original | Horizontal 320×180 e taxa 10/1 mantidas, sem crop/zoom |
| 9. Shorts verticais | Quatro MP4 reais, 1080×1920, 30 s, H.264/AAC, decodificados integralmente |
| 10. Gameplay | Trechos reais renderizados em CPU; Manager analisa, revisa e exporta |
| 11. Highlights | Três episódios reais e um episódio real de **12 minutos** a partir de trechos separados de uma fonte de 13 minutos |
| 12. NVENC | Executado na RTX 4060 disponível; resultado H.264/AAC validado |
| 13. Fallback CPU | Indisponibilidade de probe e falha em runtime simuladas; saída CPU real validada |
| 14. H.264/AAC | FFprobe de cada saída, AAC-LC e yuv420p obrigatórios |
| 15. Decodificação | Decodificação integral com FFmpeg/xerror antes do nome final |
| 16. Áudio/vídeo | Dois tons/faixas contínuos nas junções; flashes e bipes após cortes disjuntos sincronizados dentro de um quadro; DTS monotônico e lacunas de pacotes verificadas |
| 17. Sem áudio | Análise e renderização reais sem faixa de áudio |
| 18. Cancelamento/falhas | Subprocesso interrompido, corte parcial descartado, checkpoint retomado, original alterado recusado, vídeo corrompido recusado |
| 19. Progresso | Eventos derivados de `out_time_us`/blocos reais; sem avanço fictício por timer |
| 20. Originais | Identidade do arquivo de entrada inalterada após exportações e retomadas |

Legendas opcionais foram renderizadas com um transcript **de teste fornecido**, usando o agrupamento original. Isso verifica a composição e o encoder; **não é um teste de reconhecimento Whisper**.

## Limitações da validação

O navegador de teste tentou abrir `http://127.0.0.1:8765/` após o servidor informar que estava iniciado; recebeu `ERR_CONNECTION_TIMED_OUT`. A conexão do cliente Python recebeu WinError 10013. O teste por socket foi explicitamente marcado como não executado; não contamos o fluxo completo no navegador, a responsividade visual, os seletores nativos ou o botão de abrir pasta como aprovados end-to-end.

As dependências/modelos de Whisper não estavam disponíveis e a rede restringiu downloads; CUDA Whisper, FP16/INT8-FP16, VAD e batching aguardam execução com modelo local. O código os implementa em processo separado, mas a presença da RTX não valida esses recursos. **TESTAR_IA.cmd** executa um teste real opcional: escolhe um modelo existente, gera fala sintética via Windows SAPI offline, transcreve e verifica cache. Nenhuma gravação pessoal é usada. Esse teste foi incluído e compilado, mas não executado aqui.

Não foi fornecido um episódio real com a falha de áudio anterior. Os testes comprovam continuidade/sincronização dos casos sintéticos e compatibilidade estrutural H.264/AAC; não garantem recuperar problemas já presentes numa gravação real nem a qualidade subjetiva dos melhores momentos de uma live de várias horas. O player padrão do Windows não foi operado neste ambiente.

## Reprodução local

1. Extraia para uma pasta curta e execute INSTALAR.cmd.
2. Execute TESTAR.cmd; todos os testes criam somente mídia sintética temporária.
3. Execute DIAGNOSTICO.cmd para conferir a instalação atual.
4. Se desejar fala, instale as dependências, selecione um modelo e execute TESTAR_IA.cmd.
5. Abra INICIAR.cmd e confira seleção de arquivo/pasta, prévia, aprovação, cancelamento/retomada e os três modos com uma gravação curta antes de uma live inteira.

Os registros textuais da execução final e das suítes originais estão em `docs/evidencias/`. Nenhum vídeo de teste, ambiente virtual ou modelo foi incluído no ZIP.
