# AI Shorts Generator — Local Studio 1.1 (4 Shorts)

## NOVO NA 1.1: seleção editorial mais variada

Esta versão foi criada para melhorar a **escolha dos momentos**, não apenas recortar o vídeo. O ranking v2 analisa separadamente:

1. **Ação:** movimento visual, picos de movimento, intensidade e variação de áudio, termos de combate e reação.
2. **Comentário:** trechos com fala contínua, densidade de palavras, indícios de opinião e raciocínio, mantendo gameplay ao fundo.
3. **Observação/descoberta:** expressões como "olha isso", "percebi", "que detalhe", perguntas e indícios visuais.

No painel, **O que priorizar nos 4 Shorts?** permite escolher:

| Perfil | Objetivo, quando a gravação oferecer candidatos válidos |
|---|---|
| Equilibrado (padrão) | 2 ação + 1 comentário + 1 observação |
| Mais ação | 3 ação + 1 comentário |
| Mais comentários | 2 comentários + 1 ação + 1 observação |
| Mais observações | 2 observações + 1 comentário + 1 ação |

Se faltar conteúdo adequado para uma categoria, o sistema preenche a vaga com outro trecho real e sem repetição. O resultado exibe o **tipo do Short e o motivo da escolha** no navegador e no relatório. As janelas de comentários também podem começar perto do início de uma frase, em vez de depender apenas de intervalos fixos.

**OBS / faixa de microfone:** caso você tenha gravado a voz em faixa separada, clique em **Identificar faixas de áudio da gravação**, selecione essa faixa em **Faixa para analisar sua voz** e mantenha a mixagem de jogo+voz em **Faixa do áudio no Short**. Isso ajuda muito a não confundir um diálogo do jogo com um comentário seu; a escolha da faixa de renderização deve conservar todo o som desejado.

**Cache:** ao mudar apenas o perfil ou a nota mínima, o programa reaproveita a transcrição e os frames já analisados no mesmo `.local`; uma seleção diferente ainda precisa renderizar os novos Shorts. Para aproveitar o cache da 1.0, faça backup e extraia os arquivos da 1.1 **por cima da pasta de código existente**, sem apagar `.local` ou `config.local.json`. O ZIP não contém nenhum desses arquivos pessoais.

**Limite honesto:** isto ainda é uma heurística melhorada. Não identifica semanticamente uma missão, uma piada ou a identidade do falante com a precisão de uma pessoa. Só com áudio misturado, não há garantia de separar comentário do jogador e diálogo dos NPCs. Os testes novos cobrem cenários simulados; os ganhos reais dependem da sua gravação e devem ser avaliados ouvindo os 4 Shorts.

---

## NOVO: painel local no navegador — sem ChatGPT Work

Esta versão traz uma interface visual que abre **no seu navegador** e controla o processamento **no seu próprio Windows**. Nenhuma gravação é enviada para a internet e não há API paga. O primeiro download opcional do modelo Whisper é gratuito; depois funciona offline.

O painel permite escolher a gravação e a pasta de exportação (botão **Procurar** abre o seletor nativo do Windows), configurar a nota mínima e a duração, selecionar NVIDIA NVENC ou CPU, acompanhar as etapas com porcentagem e tempo, e **assistir aos quatro Shorts no navegador ao terminar**.

### Instalação rápida — PowerShell no VS Code

1. Extraia o ZIP novo em uma pasta separada, por exemplo `E:\Aulas\Projetos\AI_Shorts_Local_Studio`. Abra a pasta que contém **`main.py` diretamente**.
2. No terminal, execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py studio
```

3. A página `http://127.0.0.1:PORTA/` abrirá automaticamente. Preencha gravação e exportação. O navegador **não consegue fornecer o caminho completo de um arquivo sozinho**, então usamos o seletor nativo que aparece ao clicar em **Procurar**. Também é possível digitar o caminho do Windows.
4. **Modelo:** o ZIP contém apenas o código, sem o arquivo de modelo de quase 500 MB nem suas gravações. Para **reaproveitar seu modelo existente**, selecione no campo **Modelo Whisper** a pasta anterior que contém `model.bin`, por exemplo `E:\Aulas\Projetos\AI-Shorts-Generator\.local\models\small`. Ou, no terminal do projeto novo, execute uma vez o download grátis:

```powershell
.\.venv\Scripts\python.exe main.py prepare-model --allow-download
```

5. Clique em **Gerar meus 4 Shorts**. O painel mostrará análise de áudio, frames, seleção, render, validação e exportação. Selecione `Auto` para NVENC quando disponível; a transcrição usa CUDA se as bibliotecas NVIDIA estiverem presentes, com fallback para CPU. A qualidade **Ultra** vem selecionada por padrão (NVENC P7/CQ14; x264 CRF14), com MP4 1080×1920 e áudio AAC 320 kbps. Isso reduz perda na recompressão, mas não recupera detalhes que não existem na gravação. O NVENC não acelera necessariamente a transcrição: são etapas diferentes.

6. Mantenha o terminal aberto enquanto processa. Você pode fechar a aba e voltar ao mesmo endereço local; ao terminar, haverá quatro players de prévia e o botão **Abrir pasta**. Para encerrar o servidor, pressione `Ctrl+C` no terminal.

Como alternativa, após instalar, dê dois cliques em **`Executar.cmd`**, que agora inicia o painel. Se quiser continuar usando o terminal tradicional: `python main.py run` permanece disponível.

**Quatro Shorts de verdade:** este modo só exporta quando encontra quatro candidatos válidos, de 30 a 60 segundos cada. Se a gravação não oferecer quatro candidatos pela heurística, o painel informa quantos encontrou e sugere reduzir a nota mínima; não inventa cortes nem exporta silenciosamente apenas um ou dois. Os quatro são escolhidos por sinais visuais, áudio e palavras, não por compreensão contextual ou promessa de viralização. A nota mínima padrão é 35.

**Cache e backups:** processamento reaproveitável em `.local/runs`; configurações pessoais em `config.local.json`. O novo ZIP não contém seus modelos, vídeos nem arquivos antigos. **Não apague** a pasta original `.local/models` ou suas exportações antes de testar esta versão. É seguro manter a versão anterior como backup.

---

Projeto Python local extraído dos scripts reais de análise, legendagem, montagem e exportação. Não exige ChatGPT Work, Codex, login nem API. Nenhum vídeo é enviado para um serviço externo. Não foi publicado no GitHub.

**Limitação central:** a curadoria das execuções anteriores era feita pelo agente após inspecionar imagens e transcrições. Esse entendimento não existia nos scripts. A seleção independente implementada aqui é **heurística**, com sinais visuais, sonoros e palavras da transcrição; não equivale à compreensão de uma batalha, piada ou reação pessoal. É executável, mas não garante a mesma qualidade editorial. Veja `docs/LIMITACOES.md` e `docs/MIGRACAO.md`.

## Instalação e primeira execução

Ambiente efetivamente testado: Windows, Python **3.14.7 64 bits**. As versões em `requirements.txt` correspondem ao ambiente disponível. Instalação limpa por download não foi repetida nesta entrega; compatibilidade com outras versões de Python não foi validada.

1. Extraia o ZIP em uma pasta sua e abra essa pasta no VS Code: **Arquivo → Abrir Pasta**. O diretório deve conter `main.py` diretamente.
2. Abra **Terminal → Novo Terminal** e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py doctor
```

O FFmpeg vem no pacote `imageio-ffmpeg`; não precisa de instalação global nem alteração do PATH. Não é necessário ativar a venv ou mudar a política do PowerShell. `Instalar.cmd` oferece os dois primeiros passos. No VS Code, selecione `.venv\Scripts\python.exe` em **Python: Select Interpreter**. A extensão Python permite depuração; não é necessária para executar pelo terminal.

3. Configure os caminhos reais **apenas em `config.local.json`**, que não entra no ZIP público nem no Git:

```powershell
.\.venv\Scripts\python.exe main.py init --input "D:\Videos\live.mp4" --output "D:\Videos\Curtos"
```

Substitua os exemplos pelos caminhos de entrada e saída desejados. Também pode copiar `config.example.json` para `config.local.json` e editá-lo.

4. Modelo de transcrição: aproveite o modelo já instalado, apontando à pasta que contém `model.bin`:

```powershell
.\.venv\Scripts\python.exe main.py init --model-path "D:\Modelos\whisper-small"
```

Ou faça **uma única vez** o download gratuito explícito:

```powershell
.\.venv\Scripts\python.exe main.py prepare-model --allow-download
```

O modelo vai para `.local/models/small`. O comando de download acessa o repositório do modelo; não transmite a gravação. Sem modelo disponível, a execução para com instruções e não faz download silencioso. Para usar o modelo baixado após configurar outra pasta, deixe `model_path` vazio no JSON.

5. Execute:

```powershell
.\.venv\Scripts\python.exe main.py inspect
.\.venv\Scripts\python.exe main.py run
```

`run` faz análise integral → seleção → legendas → renderização → decodificação de verificação → cópia para o destino configurado. `Executar.cmd` abre o **Local Studio**. O comando CLI legado pode selecionar menos de quatro cortes quando faltam sinais suficientes; o **painel**, por padrão, exige quatro. As notas são proxies dos seis critérios, **não previsões de viralização**.

## Comandos por etapa e retomada

```powershell
.\.venv\Scripts\python.exe main.py scan
.\.venv\Scripts\python.exe main.py rank
.\.venv\Scripts\python.exe main.py render
.\.venv\Scripts\python.exe main.py verify
.\.venv\Scripts\python.exe main.py export
```

Use a mesma configuração nas etapas. `render` também verifica os MP4, mas não copia. Se só faltar salvar no HDD, execute `export`. Um manifesto com hashes impede duplicar uma exportação já concluída e intacta. Se existir um arquivo diferente com o mesmo nome, será usado `(2)`, `(3)` etc. A cópia não recomprime os vídeos.

Intermediários e relatórios ficam em `.local/runs/<identificador>/`. O identificador considera caminho, tamanho, data de alteração da fonte e parâmetros de análise. A transcrição salva blocos de cinco minutos; se interrompida, retoma os blocos ausentes. A varredura visual tem cache ao concluir a etapa. Mudanças de ranking, legendas ou renderização usam outro diretório de render, preservando resultados anteriores. Não rode dois processos na mesma gravação. Depois de uma interrupção abrupta, confirme que não há processo ativo antes de remover `running.lock` da execução.

O relatório `report.md` apresenta os cortes, intervalos, notas e caminhos efetivamente salvos. `ranking.json` registra todos os candidatos pontuados, evidências e seleção. As folhas `contact_*.jpg` permitem inspeção visual. O áudio original nunca é substituído na fonte.

## Configuração

| Campo | Função |
|---|---|
| `input` | Caminho da gravação, sem copiar a fonte para o projeto |
| `export_directory` | Destino dos MP4; criado se necessário |
| `data_directory` | Intermediários e modelos; padrão `.local` |
| `model_path` | Pasta local contendo `model.bin`; vazio usa `.local/models/small` |
| `language` | `null` detecta idioma por janela; `"pt"` força português e pode piorar áudio misturado |
| `audio_track` | Faixa de análise/transcrição, índice a partir de zero |
| `render_audio_track` | Faixa original incluída no MP4, normalmente uma mixagem de jogo e voz |
| `duration_seconds` | Duração alvo de 30 a 60 segundos; padrão 45 |
| `sample_seconds` | Intervalo da amostragem visual; padrão 10 segundos |
| `chunk_seconds` | Bloco de checkpoint de áudio; padrão 300 segundos |
| `minimum_score` | Limiar heurístico de seleção, sem significado de probabilidade |
| `encoder` | `auto`, `libx264` ou `h264_nvenc` |
| `quality` | `balanced`, `high` ou `ultra` (padrão: Ultra) |
| `selection_style` | `balanced`, `action`, `commentary` ou `observation` |
| `audio_track` | Faixa indexada a partir de zero, usada na seleção/transcrição (microfone separado se houver) |
| `render_audio_track` | Faixa do som no MP4; normalmente a mixagem completa |
| `transcription_device` | `auto` (tenta CUDA e recua para CPU), `cpu` ou `cuda` obrigatório |
| `label` | Texto curto acima do título; padrão GAMEPLAY |

Não há limite fixo de duas horas: o áudio é lido em blocos. Duração, espaço em disco e desempenho da CPU afetam o processamento. O WAV mono de análise ocupa aproximadamente 115 MB por hora; vídeo renderizado ocupa espaço adicional. A amostragem visual percorre a gravação inteira, mas pode perder eventos curtos entre amostras.

`auto` testa o encoder NVIDIA e usa CPU se indisponível. A decodificação é genérica, sem exigir AV1/NVIDIA. O MP4 usa H.264/AAC, 1080×1920 e taxa de quadros baseada na fonte. A montagem reaproveita a composição original: gameplay inteira centralizada sobre fundo desfocado, sem rastreamento de personagens. Preservar a tela inteira mantém HUD, mas diminui a área útil no celular.

## Ranking revisado, sem depender do Work

Para usar avaliação humana ou de um futuro avaliador local, copie `ranking.json`, edite os candidatos e a lista `selected`, preservando `source_id`. Use os seis critérios e intervalos de 30–60 s. Partes múltiplas permitem retirar uma pausa manualmente. O importador valida totais, limites, ordem temporal, duração e sobreposição:

```powershell
.\.venv\Scripts\python.exe main.py render --ranking ".local\ranking-revisado.json"
.\.venv\Scripts\python.exe main.py export
```

Cada candidato contém `rank`, `title`, `hook`, `parts` (lista de `[início, fim]` em segundos), `scores` (`visual`, `reacoes`, `entretenimento`, `narrativa`, `qualidade`, `originalidade`) e `score`. `selected` contém até quatro valores de `rank`. O arquivo gerado por `rank` é a base correta para editar. Nada exige o Work para essa revisão, mas ela não é automatizada semanticamente nesta versão.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tests\smoke_media.py
.\.venv\Scripts\python.exe tests\smoke_pipeline.py
```

`smoke_media.py --model-path "D:\Modelos\whisper-small"` também carrega o Whisper e transcreve áudio sintético local. Testes não usam lives particulares nem APIs. Resultados da entrega estão em `docs/TESTES.md`.

## Privacidade e publicação futura

O ZIP contém apenas código, configurações genéricas, documentação e testes. Não inclui venv, modelos, vídeos, áudio, transcrições, rankings pessoais ou credenciais. Caminhos pessoais ficam no arquivo local ignorado. Não existe `.env.example` porque nenhuma variável secreta ou chave de API é consumida. A flag de API paga deve permanecer falsa: não há integração de inferência remota. A publicação no GitHub depende de aprovação posterior.

Estrutura completa do pacote: `docs/ESTRUTURA.txt`.
