# Atualizar para AI Local Studio 2.0.1

Esta atualização corrige a exportação de gravações SDR em faixa de cor completa (full range), que podiam gerar a mensagem `Saída não é H.264 yuv420p` apesar de terem vídeo H.264 válido. O FFprobe identifica H.264 full range como `yuvj420p`; exigir apenas `-pix_fmt yuv420p` não eliminava a sinalização de faixa completa da fonte.

## Instalação existente

1. Interrompa o trabalho pelo Studio e feche a janela do servidor aberta por INICIAR.cmd. Feche também a aba do Studio.
2. Extraia o novo ZIP em uma pasta temporária.
3. Copie **o conteúdo** da pasta `AI-Local-Studio` extraída para a pasta em que você já tem INSTALAR.cmd e INICIAR.cmd. Aceite substituir os arquivos do programa.
4. Mantenha sua `.venv`, `.local`, `tools` e pastas de saída. O novo ZIP não inclui essas pastas e não é necessário apagá-las ou reinstalar dependências.
5. Abra INICIAR.cmd novamente. O cabeçalho deve mostrar **2.0.1**. Se estiver na versão antiga, atualize a página com Ctrl+F5.
6. Use **Recuperar última sessão** e **Retomar**, ou analise novamente o mesmo vídeo no modo desejado. O cache da análise continua compatível. Os intermediários de renderização antigos são ignorados pela nova assinatura do renderizador.

Os MP4s de saída usam uma nova assinatura no nome; exportações antigas não são substituídas. A etapa de renderização do trabalho interrompido precisa ser refeita. Não é necessário reanalisar áudio e imagem que já estejam em cache.

## Instalação nova

Extraia para `E:\AI-Local-Studio`, execute INSTALAR.cmd e depois INICIAR.cmd, como na versão anterior.

## O que mudou

- Conversão efetiva de amostras full range para limited range, com metadados coerentes. Não é apenas uma troca do nome do formato: os níveis são convertidos para preservar a aparência de pretos/brancos.
- A correção acontece no renderizador compartilhado por **Shorts, Gameplay e Highlights**, com libx264 ou NVENC.
- A validação continua exigindo H.264/yuv420p: não foi desativada ou enfraquecida para aceitar um resultado diferente do solicitado.
- Mensagem de falha de formato agora informa codec, pixel format e faixa observados, além de gravar um diagnóstico `.failure.json`.
- O aviso genérico sobre gravação corrompida/amostras ausentes foi removido das exceções sem relação com a entrada.

O mesmo erro foi reproduzido com fonte sintética full range antes da correção. Isso demonstra um defeito real do pipeline 2.0, mas a captura de tela sozinha não confirma todos os metadados da gravação particular de Final Fantasy. Se o erro persistir após a atualização, o novo diagnóstico informa exatamente o formato encontrado.
