# Relatório do pacote — 21/11/2026

## Conteúdo e preservação

Três projetos separados: AI Shorts Generator 1.1, AI Gameplay Editor Alpha 0.3 e AI Highlights Generator 1.0. Os dois primeiros foram extraídos dos ZIPs locais fornecidos e comparados byte a byte. Os arquivos ZIP originais também são incluídos intactos em `Originais`. O manifesto registra tamanho e SHA-256 de cada arquivo de projeto e de cada ZIP original.

O novo código foi revisado à luz do ranking e validação do Shorts e da análise, planejamento e renderização do Gameplay. As diferenças necessárias à exportação sem perdas e aos episódios longos estão documentadas em `AI_Highlights_Generator_1_0/REFERENCIAS_DE_CODIGO.md`.

## Testes executados nesta montagem

| Projeto | Testes | Resultado |
| --- | --- | --- |
| Shorts 1.1 | Suíte original `test_core.py`: cache, bloqueio, ranking por categorias, intervalos, legendas e exportação | 9 aprovados |
| Gameplay 0.3 | Suítes originais `test_planner.py` e `test_gpu_progress.py`: planejador, cronologia, fallback GPU e progresso | 13 aprovados |
| Highlights 1.0 | Suíte com mídia sintética, CPU, GPU, seleção, preservação e handlers locais | 20 aprovados, 3 testes HTTP por socket não executados |

Total: **42 testes aprovados**. Os testes dos originais foram executados em cópias descartáveis separadas, para manter as pastas entregues intactas. Não foi repetida a instalação limpa de todas as dependências do Shorts, nem sua transcrição Whisper ou renderização completa. As demais suítes originais seguem disponíveis, sem alteração.

No Highlights, uma fonte sintética de 13 minutos produz um episódio real de 12 minutos com dois intervalos separados. São comparados todos os hashes de quadros e todos os samples PCM de duas faixas de áudio, em CPU e em NVDEC/NVENC. Também foram testados CUDA na redução para análise, vídeo SDR 10 bits, corte fracionário, fonte sem áudio e cadência VFR. A pontuação PyTorch CUDA opcional não foi executada, pois PyTorch não está instalado no Python de teste.

## Limites da validação

O ambiente Windows bloqueia conexões locais por socket (WinError 10013), e o navegador de teste recebeu timeout ao acessar o servidor. Os três testes de conexão HTTP foram deixados como skipped; os handlers HTTP foram exercitados em memória. Não foi validado o fluxo visual completo nem o seletor nativo no navegador. Isso está explícito nas instruções do novo projeto.

Nenhum teste usou gameplay real ou avaliou subjetivamente a seleção dos melhores momentos. As heurísticas podem preferir movimento de câmera/música e perder cenas importantes mais calmas. O usuário deve revisar o plano. O Highlights não preserva metadados HDR especiais nesta versão e recusa as fontes detectadas, sem conversão silenciosa.

## Integridade

Execute `python verificar_integridade.py` na raiz. A verificação lê o manifesto e os arquivos, sem escrever neles. Arquivos novos criados pelo uso normal, como `.venv` e caches, não invalidam a comparação dos arquivos distribuídos; arquivos distribuídos alterados ou ausentes são apontados. Na montagem, o ZIP final também passou por teste CRC e por comparação de cada arquivo original com as entradas dos ZIPs de origem.
