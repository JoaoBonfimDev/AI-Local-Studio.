# AI Local Studio — três projetos independentes

Este pacote reúne os dois projetos originais e o novo AI Highlights Generator 1.0, cada um em sua pasta. Extraia o ZIP inteiro para uma pasta nova, por exemplo `E:\Projetos\AI_Local_Studio`. Não extraia por cima das instalações que você já utiliza.

| Pasta | Finalidade | Como iniciar |
| --- | --- | --- |
| `AI_Shorts_Generator_1_1` | Quatro Shorts com os recursos originais da versão 1.1 | Execute o `Instalar.cmd` dessa pasta e depois `Executar.cmd`. Leia o README sobre o modelo Whisper existente. |
| `AI_Gameplay_Editor_0_3` | Gameplay completo ou melhores momentos, com o painel de renderização original | Execute `python main.py doctor` nessa pasta. Os comandos `run` e `render` abrem o painel durante a renderização no Windows. Consulte o README original. |
| `AI_Highlights_Generator_1_0` | Até dez episódios cronológicos de 10–15 minutos, sem repetir intervalos | Execute `INSTALAR.cmd` dessa pasta uma vez e depois `INICIAR.cmd`. Abre http://127.0.0.1:8767 . |

## Começar pelo Highlights

1. Instale Python e FFmpeg/FFprobe conforme `AI_Highlights_Generator_1_0/INSTALACAO_WINDOWS.md`.
2. Execute `INSTALAR_HIGHLIGHTS.cmd` na raiz deste pacote.
3. Execute `INICIAR_HIGHLIGHTS.cmd` e mantenha o terminal aberto.
4. Selecione o vídeo e a pasta de saída, escolha os limites e clique em **Analisar e montar plano**.
5. Revise os intervalos; depois clique em **Renderizar episódios**.

O novo programa usa CUDA/NVDEC/NVENC quando os testes de compatibilidade passam. A saída é MKV sem perdas de pixels decodificados, com todas as faixas de áudio em PCM. Não aplica legendas, efeitos, zoom ou crop. Resolução e cadência dos quadros são mantidas nos formatos suportados. HDR PQ/HLG e metadados HDR especiais são recusados explicitamente nesta versão. Arquivos sem perdas podem ocupar muito mais espaço que o original.

“Até dez” é um teto: se faltar material elegível, serão criados menos episódios ou nenhum. Não são repetidos trechos para completar minutos. A seleção é heurística audiovisual, sem reconhecimento semântico do jogo. A interface permite revisar e ajustar os tempos antes de renderizar. Os alvos de 11–14 minutos deixam margem dentro dos limites de 10–15.

## Originais preservados

As pastas Shorts e Gameplay contêm exatamente os arquivos dos ZIPs fornecidos, sem patches ou substituições. Seus recursos e limitações originais permanecem iguais. Os ZIPs de entrada também estão guardados em `Originais` e podem ser recuperados separadamente.

Não há ambiente virtual compartilhado. Instale e execute cada projeto dentro da pasta correspondente; é seguro manter seus projetos atuais e esta cópia separados. O pacote não inclui gravações, modelo Whisper, bibliotecas CUDA, drivers ou ambientes `.venv`. O uso é local e sem APIs pagas; a instalação de dependências e o download opcional inicial do modelo do Shorts podem precisar de internet.

Para verificar hashes dos arquivos distribuídos:

```powershell
python verificar_integridade.py
```

Consulte `RELATORIO_DO_PACOTE.md` para os testes, e o README de cada pasta para instruções completas. O fluxo visual do Highlights ainda precisa ser conferido em um Windows que permita acesso ao servidor local: este ambiente bloqueou a conexão do navegador.
