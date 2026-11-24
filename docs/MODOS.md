# Operação dos três modos

## Arquivo e faixas

Selecione um MP4/MKV/MOV/AVI/WebM/M4V/TS local já finalizado. O programa exige uma única faixa de vídeo. Não edita gravações ainda em escrita pelo OBS. Caminhos de rede/URL não são aceitos. Escolha uma pasta local para os resultados; preencha o nome do jogo para organizar os MP4s em `Saída/Jogo/Modo`. Cada sessão tem dados técnicos próprios em `Saída/Jogo/.studio/`, separados dos vídeos. Se o nome ficar vazio, o Studio usa o nome da gravação.

Os índices de áudio começam em zero. Faixa para análise escolhe a trilha usada para energia e transcrição. Faixa no Short escolhe a trilha do MP4 vertical. Nos modos horizontais todas as faixas de áudio existentes são mantidas separadamente e convertidas para AAC-LC, até 320 kbps por faixa. A ordem das faixas segue a fonte. Se jogo e microfone estiverem misturados, permanecem misturados; o programa não presume separação.

## Shorts

O ranking reaproveitado atribui notas visual/reação/entretenimento/narrativa/qualidade/originalidade e tenta variar ação, comentários e observações. Movimentação e palavras são indícios; rotação de câmera pode parecer combate. A nota mínima e a prioridade alteram somente a seleção. Quatro é a meta e o máximo, não uma obrigação de repetir conteúdo. A revisão recusa intervalos sobrepostos. Cada Short deve totalizar 30–60 segundos.

O vídeo inteiro é encaixado na composição vertical anterior, sobre fundo desfocado. Não há rastreamento de personagem ou crop do primeiro plano. As legendas opcionais usam palavras com timestamps; não há texto, título ou logo obrigatório. Elas exigem a transcrição local ativada.

## Gameplay

Completa usa o planejador conservador original: baixa energia e movimento por pelo menos o intervalo de inatividade escolhido, com margem de contexto. Uma fonte completamente silenciosa/estática é preservada em vez de descartada. Melhores momentos usa o planejador original de atividade acrescido de pesos configuráveis para fala e expressões. Não há teto de tempo ou de número de cortes para gameplay; o validador admite até 10.000 trechos por plano para limitar o tamanho das solicitações.

## Highlights

Reutiliza o conceito original de selecionar blocos pontuados, excluir silêncio/quadros estáticos e ordenar cronologicamente. Os blocos de contexto agora são configuráveis (padrão 30 s), usam os mesmos dados compartilhados e não exigem alvos fixos de 11–14 minutos. A interface aceita 0,1–1440 minutos como alvo, útil inclusive para testes; para uso normal comece em 10–15 minutos. O máximo é 10 episódios. A escolha de um alvo alto nunca adiciona cenas artificiais para alcançá-lo.

Os pesos de fala/expressões e a sensibilidade influenciam a escolha. O último episódio pode ficar menor; o plano informa isso. Remova sua aprovação se não quiser exportá-lo. Os episódios não reutilizam intervalos e mantêm a sequência original.

## Revisão

A lista mostra tempos em segundos no original. Você pode ajustar início/fim e rejeitar trechos inteiros. Episódios que ficarem vazios são removidos ao enviar a revisão. A ordem deve continuar cronológica, inclusive entre episódios. Não se pode exportar um plano vazio ou fora da fonte. A prévia é uma cópia temporária de até 60 segundos do trecho, em resolução reduzida; sua qualidade não representa a qualidade final.

O plano original e o plano aprovado são gravados em JSON. Rankings e transcrições também ficam na subpasta da execução. A interface cobre edição dos intervalos e aprovação; não inclui um editor com arrastar clipes, waveform, diarização, identificação semântica de bosses ou reconhecimento de cenas por um modelo visual.

## Qualidade

| Perfil | NVENC | libx264 | AAC por faixa |
| --- | --- | --- | --- |
| Equilibrado | p4, CQ 21 | faster, CRF 20 | 192 kbps |
| Alta qualidade | p6, CQ 17 | slow, CRF 17 | 256 kbps |
| Ultra | p7, CQ 14 | slow, CRF 14 | 320 kbps |

Todas as saídas finais são MP4 H.264/yuv420p/AAC-LC/faststart. Ultra é qualidade elevada, não preservação bit a bit. FPS médio de fontes VFR passa a CFR; essa limitação é explícita. Fontes SDR 10 bits passam a 8 bits para compatibilidade. HDR é recusado, sem tone mapping silencioso.
