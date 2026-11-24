# Validação 2.0.2 — GPU explícita e organização por jogo

Data: 23/11/2026, São Paulo.

**Resultado:** 34 testes executados em 117,485 s: **33 aprovados, 1 não executado** por bloqueio de conexão localhost. Sem falhas na execução final. Python 3.14.7 em ambiente virtual isolado e RTX 4060 disponíveis.

## Novos cenários testados

| Cenário | Verificação |
| --- | --- |
| Nome digitado | Texto Unicode, espaços, caracteres proibidos do Windows, nomes de dispositivos como CON/NUL e limite de comprimento |
| Pastas de jogo/modo | Manager cria `GTA 6/Gameplay - Melhores momentos` para vídeos e `.studio/<sessão>` para os dados técnicos |
| Nome de vídeo | Exportação real `GTA 6 - Gameplay longa - Melhores momentos.mp4` |
| Pasta limpa | Somente o MP4 na pasta dos vídeos; relatórios e intermediários permanecem na área técnica |
| Colisão com arquivo anterior | Arquivo anterior preservado byte a byte; novo vídeo ganha `(2)` |
| Recuperação da sessão | Pasta de exportação e nome do jogo mantidos; retomada não cria uma cópia extra |
| GPU escolhida após análise CPU | Análise real feita na CPU; renderização real em h264_nvenc na RTX 4060; scanner proibido por mock durante o render, comprovando que não houve reanálise |
| GPU obrigatória indisponível | NVENC indisponível simulado; operação informa erro e não cai silenciosamente para CPU |

A regressão mantém os testes anteriores: full range nos três modos/encoders, quatro Shorts verticais, episódio real de 12 minutos, múltiplas faixas de áudio, continuidade, sincronização, cache, retomada, fallback automático e validação completa do MP4.

## GPU: alcance da implementação

O Studio já suportava h264_nvenc, mas o modo automático podia recuar para CPU e o painel não mostrava o codificador durante a tarefa. A versão 2.0.2 torna **GPU NVIDIA — NVENC** a opção inicial e mostra o codificador confirmado pelo renderizador. A revisão permite escolher encoder e qualidade sem reanálise. A opção automática com fallback continua disponível de forma explícita.

Não foi migrada a composição visual completa para CUDA: filtros verticais, conversão de cor, áudio e validação podem usar CPU. Os testes reais confirmam o encoder NVENC e a análise com NVDEC/scale CUDA na RTX 4060 observada; não prometem 100% de uso de GPU nem que todas as etapas sejam aceleradas.

## Compatibilidade de sessões e arquivos

Sessões criadas em versões antigas continuam usando seus destinos antigos. Novos trabalhos usam a organização por jogo. O cache audiovisual/transcrição não inclui nome do jogo ou destino e continua reutilizável. A assinatura dos intermediários de renderização inclui os destinos e nomes para impedir que uma mudança de organização publique arquivos com o nome de outra execução.

Nenhuma exportação antiga é movida ou sobrescrita. Os vídeos originais continuam somente leitura. Não houve instalação global, publicação no GitHub, push ou merge.

## Limitações de validação

O ambiente continua bloqueando o cliente HTTP localhost (WinError 10013); o teste de conexão real é marcado como não executado. Os handlers são exercitados em memória. A interface nova passou por verificação de sintaxe JavaScript e seus controles estão ligados aos endpoints/Manager testados, mas o fluxo visual completo permanece sem validação end-to-end neste ambiente. A transcrição real Whisper continua dependente das bibliotecas/modelos locais descritos na documentação anterior.

Resultado detalhado da suíte final: `evidencias/test-run-2-0-2-final.txt`.
