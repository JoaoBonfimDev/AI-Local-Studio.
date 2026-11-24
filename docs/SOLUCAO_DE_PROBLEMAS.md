# Solução de problemas

| Sintoma | Ação |
| --- | --- |
| INICIAR pede instalação | Execute INSTALAR.cmd dentro da pasta extraída. A pasta `.venv` precisa pertencer a esta instalação. |
| Python não encontrado | Instale Python 3.13/3.14 de python.org com PATH e Tcl/Tk. Reabra o instalador. O launcher `py` sem runtimes cadastrados pode falhar; `python` é tentado primeiro. |
| Dependência sem wheel | O vídeo funciona sem transcrição. Confira se o erro é de versão ou rede. Use INSTALAR_IA.cmd; se faltar wheel de 3.14, prepare nova instalação com 3.13. |
| FFmpeg ausente e sem internet | Coloque `ffmpeg.exe` e `ffprobe.exe` de uma distribuição confiável em `tools/` ou use os executáveis já no PATH. Reexecute INSTALAR.cmd. |
| Navegador não abre | Acesse o endereço que aparece no terminal. O servidor usa somente 127.0.0.1. Verifique se já existe outra instância na porta 8765. |
| WinError 10013 / localhost bloqueado no ambiente de desenvolvimento | A entrega registra esse bloqueio. Execute o programa diretamente no Windows fora do ambiente restrito. Não é necessário expor o servidor na rede nem desativar proteções do Windows. |
| Seletor nativo não aparece | Aguarde operações ativas e confira Tcl/Tk. Cole o caminho no campo como alternativa. Não faça upload do vídeo para serviços externos. |
| CUDA/cuBLAS/cuDNN ausente | Use diagnóstico e transcrição Automática/CPU. Confira as DLLs da instalação Python atual e CUDA_PATH/CUDNN_PATH. |
| Modelo ausente | Selecione uma pasta Faster-Whisper com `model.bin` ou use Baixar modelo. Nenhum modelo é baixado silenciosamente durante a análise. |
| Poucos Shorts ou Highlights curtos | Ajuste nota/sensibilidade, ative a transcrição com modelo local ou escolha uma gravação mais rica. O sistema não duplica cenas para completar a meta. |
| Áudio não é a mixagem desejada | Confira índices de faixa na configuração. Nos Shorts, escolha a faixa de exportação. Nos horizontais, todas as faixas são preservadas separadas; seu player escolhe qual reproduzir. |
| Erro de decodificação na entrada | Confira a gravação original no mesmo intervalo. O Studio não reconstrói dados que já estavam ausentes/corrompidos. Uma falha na entrada impede que a operação seja declarada concluída. |
| Cancelou/fechou durante o trabalho | Reabra, recupere a última sessão e retome. Blocos/cortes finalizados são usados; uma operação FFmpeg incompleta reinicia aquele corte. |
| Sem espaço em disco | Interrompa. Finais de alta qualidade e PCM temporário podem ocupar bastante espaço. As estimativas são aproximadas e o Studio não apaga seus vídeos. Escolha um disco com folga. |
| Caminho longo ou caracteres especiais | Prefira `E:\AI-Local-Studio` e uma pasta curta de saída. O Windows/FFmpeg pode limitar caminhos muito longos. Aspas, espaços e Unicode comuns são passados sem shell. |

Logs resumidos aparecem na interface; os estados, planos e relatórios ficam na subpasta da execução. `DIAGNOSTICO.cmd` mostra capacidades locais. `TESTAR.cmd` usa apenas mídia sintética.

Os testes de áudio verificam tons sintéticos contínuos e flashes/bipes sincronizados em vários cortes. Eles não comprovam a recuperação de uma gravação problemática específica, pois esse arquivo de teste real não foi fornecido nesta solicitação. A qualidade da seleção e cortes de diálogos deve ser revisada pelo usuário.
