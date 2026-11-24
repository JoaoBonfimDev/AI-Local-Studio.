# Validação da correção 2.0.1 — 23/11/2026

**Resultado final:** 29 testes na suíte integrada: **28 aprovados e 1 não executado** por bloqueio de localhost. Os casos full range passaram nos três modos, em CPU e NVENC.

## Problema reproduzido

O erro relatado nos Shorts foi reproduzido no renderizador 2.0 com um vídeo SDR full range. O FFprobe da fonte e do MP4 exportado informou `codec_name=h264`, `pix_fmt=yuvj420p`, `color_range=pc`. Isso ocorreu tanto com libx264 quanto com h264_nvenc, apesar de o comando do encoder conter `-pix_fmt yuv420p`.

A validação exigia H.264/yuv420p e rejeitou corretamente a saída fora do contrato. O defeito estava no pipeline: ainda permitia herdar faixa completa da entrada. O texto genérico sobre amostras ausentes era acrescentado a qualquer exceção e confundia uma falha de formato na saída com possível corrupção da entrada.

Não foi recebido o arquivo privado de Final Fantasy nem seu FFprobe. Portanto, não é possível afirmar somente pela captura de tela que seus metadados são exatamente os da fonte sintética. A correção cobre um caso real e reproduzível que gera a mesma mensagem, e amplia o diagnóstico para casos restantes.

## Correção

- O filtro compartilhado converte amostras full range para limited range, informa a faixa correta ao encoder e gera H.264/yuv420p.
- Os valores de pixel são convertidos antes da composição vertical. Não é feita apenas uma alteração dos metadados, que poderia mudar a aparência dos níveis de preto/branco.
- A correção se aplica aos três modos, em CPU/libx264 e GPU/h264_nvenc.
- A versão da assinatura de renderização mudou. Intermediários antigos não são reutilizados; o cache de análise continua válido.
- O validador continua estrito. Em uma falha de formato, informa codec/pixels/faixa observados e grava `.failure.json`.
- Foi retirado o aviso genérico de corrupção de entrada de exceções sem relação com a gravação original.

## Testes específicos

| Cenário | Verificação |
| --- | --- |
| Fonte full range em Shorts, CPU | MP4 real de 30 s, 1080×1920, H.264/yuv420p, uma faixa AAC, decodificação completa |
| Fonte full range em Shorts, RTX 4060/NVENC | Mesmo contrato validado com encoder GPU real |
| Fonte full range em Gameplay, CPU e NVENC | Trechos separados concatenados, enquadramento original, duas faixas AAC, decodificação completa |
| Fonte full range em Highlights, CPU e NVENC | Mesmo contrato validado por ambos os encoders, sem falhas de pacotes de áudio |
| Níveis de preto/branco | Comparação RGB da fonte e do final; erro médio inferior a 4/255, preto abaixo de 4 e branco acima de 250 |
| Diagnóstico de erro remanescente | Saída full range deliberadamente inválida é recusada com valores observados e relatório `.failure.json` |

H.264 pode omitir a sinalização explícita de faixa quando usa o padrão limited; nesse caso o FFprobe também pode omitir `color_range`. O teste exige yuv420p, recusa pc/full range e confirma os níveis na imagem decodificada. Não inventamos primárias ou matriz de cor quando a fonte não as informa.

A suíte completa mantém os testes de quatro Shorts, episódio real de 12 minutos, fontes sem áudio, continuidade dos tons nas junções, sincronização flash/bipe, cache, retomada, fallback CPU e segurança dos handlers. O resultado final está em `evidencias/test-run-2-0-1-final.txt`.

## Limites que continuam

O teste de conexão HTTP por socket continua bloqueado pelo ambiente de desenvolvimento. A transcrição real Whisper ainda requer bibliotecas/modelo local; sua validação não faz parte desta correção. Não houve push ou merge no GitHub.

Instruções para aplicar a atualização mantendo `.venv`, modelos e cache: [ATUALIZAR_2_0_1.md](ATUALIZAR_2_0_1.md).
