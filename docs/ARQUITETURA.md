# Arquitetura e integração dos códigos existentes

## Base auditada

Entrada: `AI Local Studio.zip`, 23.432.280 bytes, SHA-256 `41e2297d8b7316b4556e218d163845d172a1152f613fabef5879ea49bf2dc14b`.

O arquivo tinha 2.953 entradas, incluindo um ambiente `.venv`, diretórios repetidos e caches Python. Foram inventariadas todas as entradas; para o trabalho de integração foram extraídos os fontes, testes, configurações, interfaces e documentação, excluindo dependências instaladas e caches. A extração literal inicial encontrou o limite de comprimento de caminho do Windows dentro de `.venv`; isso não exige ou justifica distribuir esse ambiente. Os 72 arquivos autorais/arquivos de origem resultantes foram lidos e tiveram tamanho/hash registrados em FONTES_AUDITADAS.json; os ZIPs originais internos também foram inventariados.

## Reutilização concreta

| Origem | Reutilização na aplicação 2.0 |
| --- | --- |
| Shorts `ranking.py` | Chamado diretamente por `modes/shorts.py`: seis notas, expressões, categorias, diversidade e seleção até quatro |
| Shorts `render.py` | Reutiliza `ass_time`, `ass_text`, `caption_groups`; composição vertical original adaptada em `render/video.py` |
| Gameplay `media.py` | `build_activity`/percentis utilizados diretamente; extração PCM e diferença de quadros adaptadas para blocos/checkpoints |
| Gameplay `planner.py` | `full_gameplay`, `best_moments`, `merge_intervals` chamados diretamente |
| Gameplay `render.py` | `QUALITY_PRESETS` reutilizados diretamente; nova execução cancelável e validação ampliada |
| Highlights `media.py` | `Cancelled` reutilizado; Runner adaptado, baseado no subprocesso sem shell e buffers em disco |
| Highlights `selection.py` | Conceito de blocos pontuados, gate absoluto de atividade, orçamento e cronologia adaptados sem limites rígidos 600–900 s |
| Highlights/Shorts servidores | Interface única usa as proteções Host/Origin/token e streaming Range; seus servidores antigos não são iniciados |

Os módulos anteriores foram preservados em `legacy/` para rastreabilidade e importação das funções comuns. Seus antigos entrypoints e testes ficam como referência, não constituem três serviços da aplicação nova. Documentação histórica pode mencionar formatos ou recursos antigos e não substitui README/documentação 2.0.

## Dados e execução

`Manager` executa apenas uma tarefa pesada por vez. Análise visual e sonora usam arquivos temporários de até 60 s em resolução reduzida e descartam o bloco após extrair sinais. Um modelo de fala é carregado em um subprocesso separado; áudio de 30 s por vez e transcrição incremental. Cada etapa tem configuração/cache próprios. Nenhum vídeo completo fica em RAM.

Seleção lê os sinais compartilhados e cria planos por modo. Revisão não altera o cache. O renderizador recebe somente os intervalos aprovados; todos os nomes de intermediários são gerados internamente. H.264/PCM NUT por trecho é montado com duração explícita; uma única codificação AAC e faststart formam o final. A validação ocorre no arquivo parcial; somente depois há renomeação para MP4 final. Uma falha GPU automática elimina intermediários daquela assinatura e reinicia na CPU, evitando misturar encoders.

Cache: identidade com caminho resolvido/tamanho/mtime e SHA-256 de até três amostras de 1 MiB, versão de algoritmo e configurações por etapa. Não é um hash integral da gravação. Modelos são identificados por caminho, tamanho e mtime de model.bin. Mudanças em configurações de seleção/render não invalidam análise compatível. JSONs usam escrita temporária e substituição atômica.

## Progresso e cancelamento

FFmpeg fornece segundos processados via `-progress`; cache informa blocos realmente recuperados; Whisper informa janelas concluídas por arquivo de progresso. ETA é da etapa. Carregamento de modelo e download sem medição disponível são indeterminados. Interromper mata o processo ativo e conserva checkpoints concluídos. Retomar recomeça apenas a unidade incompleta; não há pausa no meio de um encoder FFmpeg.

## Áudio: diagnóstico e correção

O Highlights anterior favorecia igualdade de pixels/PCM e saída MKV, incompatível com o objetivo de reprodução padrão do Windows. O Gameplay concatenava MP4s com AAC codificado separadamente, sujeito a priming/padding por trecho. O novo caminho evita AAC intermediário, normaliza PTS e amostras e só codifica AAC no final. A correção foi medida com tons contínuos em junções e flashes/bipes sincronizados, com múltiplas trilhas. Não foi recebido um exemplo real dos episódios com áudio quebrado; não é possível atribuir todos os problemas anteriores a uma causa única nem afirmar que defeitos existentes na fonte serão recuperados.
