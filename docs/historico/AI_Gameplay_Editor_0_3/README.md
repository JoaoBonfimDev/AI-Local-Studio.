# AI Gameplay Editor — Alpha 0.3

Editor **local** para gameplays gravadas no OBS ou capturadas no console. Cria vídeos horizontais em MP4, preservando a sequência dos acontecimentos. **Sem login, API paga, upload ou duração máxima predefinida.**

> Projeto independente do `AI-Shorts-Generator`. O projeto antigo permanece intacto. Nesta Alpha, a seleção é **heurística**, baseada em áudio e movimento: ainda **não existe IA semântica** para reconhecer de modo confiável chefes, humor, missões ou cenas emocionantes. O suporte NVDEC acelera **somente a decodificação**, quando disponível, e não melhora sozinho o entendimento dos acontecimentos.

## Dois modos

| Modo | CLI | O que acontece |
| --- | --- | --- |
| Gameplay completo | `completo` ou `full` | Preserva o vídeo inteiro, exceto períodos longos de pouco movimento **e** quase silêncio; mantém segundos antes/depois de cada corte. |
| Melhores momentos | `melhores` ou `highlights` | Classifica atividade visual e sonora, seleciona trechos com margem de contexto e une tudo cronologicamente. Sem limite de quantidade de trechos. |

## Requisitos

- Windows 10/11 com Python **3.10+** (funciona com a linha 3.14, sem dependências Python externas).
- [FFmpeg e FFprobe](https://ffmpeg.org/download.html) instalados e presentes no `PATH`.
- Espaço no disco para os cortes temporários e o MP4 final (vídeos longos podem ocupar muitos GB).
- Compatível com o PC de referência: Ryzen 7 5700X, RTX 4060 8 GB, 16 GB de RAM. A GPU é opcional; a comparação de imagens e o ranking ainda rodam na CPU.

**Alpha 0.3:** o editor tenta decodificar frames com **NVDEC/CUDA** na GPU, mas ainda calcula a diferença visual na CPU. A renderização usa NVENC quando disponível, com três perfis de qualidade. Um **painel visual privado no navegador** acompanha a exportação em tempo real.

Não é necessário `pip install` para usar esta versão. O primeiro teste deve ser feito com 5 a 15 minutos de gravação em SDR, de preferência com áudio.

## Começando no seu Windows (PowerShell)

1. Extraia a Alpha 0.3 em `E:\Aulas\Projetos\AI_Gameplay_Editor_Alpha_0_3`. **Nesta versão, `main.py` está diretamente na raiz do ZIP**, sem subpasta `ai-gameplay-editor`! Mantenha as versões antigas sem substituí-las enquanto estiverem em execução.
2. Abra o PowerShell ou o terminal do VS Code nessa pasta:

```powershell
cd "E:\Aulas\Projetos\AI_Gameplay_Editor_Alpha_0_3"
python --version
ffmpeg -version
python main.py doctor
```

3. Substitua **somente** o caminho do vídeo pelos seus arquivos reais (MP4, MKV etc.). Exemplo do modo **gameplay completo**:

```powershell
python main.py run --input "E:\Gravacoes\GTA6\gravacao01.mkv" --output-dir "E:\Gravacoes\GTA6\editados" --mode completo --decode auto --encoder auto
```

4. Para **melhores momentos** do mesmo vídeo, reaproveitando a análise anterior:

```powershell
python main.py run --input "E:\Gravacoes\GTA6\gravacao01.mkv" --output-dir "E:\Gravacoes\GTA6\editados" --mode melhores --sensitivity 60 --decode auto --encoder auto
```

> `E:\Gravacoes\GTA6\gravacao01.mkv` é **apenas um exemplo**: coloque o caminho do arquivo que você realmente tiver no PC. Se FFmpeg não aparecer no PowerShell, instale-o, configure o PATH e abra o terminal novamente.

### Resultados no diretório de saída

```text
editados/
├── analise.json              # cache de áudio, movimento e atividade por segundo
├── timeline_full.json        # cortes do modo gameplay completo
├── timeline_highlights.json  # cortes do modo melhores momentos
├── gameplay_full.mp4         # vídeo montado em modo completo
└── gameplay_highlights.mp4   # vídeo montado em modo destaques
```

O vídeo **original nunca é modificado**. A timeline pode ser editada manualmente.

Se o modo completo não encontrar nenhum corte, ele salva a timeline e **não renderiza novamente o vídeo inteiro**. Nesse caso, a gravação original já é o resultado e nenhuma exportação é necessária. Isso evita perder horas e espaço em disco.

## Novo: renderização com painel visual no navegador

Você pode continuar utilizando sua timeline da Alpha 0.2! **Nenhuma nova análise é necessária.** Exemplo de exportação em qualidade máxima:

```powershell
python main.py render --timeline "E:\Gravações\editados\timeline_highlights.json" --output "E:\Gravações\editados\melhores_momentos_ultra.mp4" --encoder auto --quality ultra
```

No **Windows**, ao executar `render` ou `run`, a Alpha 0.3 abre automaticamente uma aba do navegador padrão com:

- Indicador circular e barra de progresso geral estimado;
- Etapa atual: preparação, renderização, junção, validação ou conclusão;
- Número do trecho em processamento, tempo decorrido e ETA aproximado;
- Perfil de exportação, resolução, codificador e destino;
- Linha visual com o progresso de até 160 blocos representativos dos cortes.

O endereço é `http://127.0.0.1:PORTA/`: funciona somente no próprio PC, sem site público ou APIs externas. **Mantenha o PowerShell aberto enquanto renderiza.** Ao terminar, use o botão **Encerrar painel** para fechar o servidor local.

Se a aba não abrir automaticamente, o terminal exibirá o endereço local para você colar no navegador.

Para manter as barras antigas somente no PowerShell, acrescente `--terminal`. Em Linux/macOS, acrescente `--ui` para abrir o painel.

### Perfis de qualidade de renderização

| Opção CLI | Nome | NVIDIA NVENC | CPU (alternativa) | Áudio AAC |
| --- | --- | --- | --- | --- |
| `--quality balanced` | Equilibrada | CQ 21, preset P4 | CRF 20, faster | 192 kbps |
| `--quality high` | Alta qualidade (**padrão**) | CQ 17, preset P6 | CRF 17, slow | 256 kbps |
| `--quality ultra` | Qualidade máxima prática | CQ 14, preset P7 | CRF 14, slow | 320 kbps |

Valores CQ/CRF mais baixos priorizam a preservação visual. **Ultra gera arquivos potencialmente muito maiores, ocupa mais espaço temporário e pode renderizar mais devagar.** A exportação mantém a resolução e a taxa de quadros da fonte quando possível; não cria novos detalhes que não existiam na gravação original.

## Analisar antes de renderizar (recomendado para as primeiras gravações)

Primeiro, só planeje os cortes:

```powershell
python main.py analyze --input "E:\Gravacoes\GTA6\gravacao01.mkv" --output-dir "E:\Gravacoes\GTA6\revisao" --mode melhores --sensitivity 60
```

Depois, abra `timeline_highlights.json` no VS Code. Cada entrada em `clips` possui `name`, `start` (segundos) e `end` (segundos). Você pode ajustar o início, o fim, a ordem, excluir ou adicionar trechos. **A ordem da lista é a ordem do vídeo final.** Não altere o bloco `source`.

Por último, renderize a timeline revisada:

```powershell
python main.py render --timeline "E:\Gravacoes\GTA6\revisao\timeline_highlights.json" --output "E:\Gravacoes\GTA6\revisao\video_final.mp4" --encoder auto --quality high
```

## Ajustes de comportamento

- `--sensitivity 0..100` (somente modo melhores): valores maiores **selecionam mais** momentos; padrão 50.
- `--min-idle 20` (somente completo): só remove intervalos com pelo menos 20 segundos de baixa atividade.
- `--audio-floor 0.008` (somente completo): limiar RMS de quase silêncio; aumentá-lo pode remover partes com música baixa. **Use com cuidado para não perder diálogos.**
- `--motion-floor 0.065` (somente completo): limiar de pouca mudança visual; aumentar pode eliminar trechos de câmera parada.
- `--sample-seconds 3`: uma imagem amostrada a cada 3 segundos; `1` faz uma análise visual mais detalhada e demorada.
- `--decode auto`: tenta usar o decodificador NVIDIA NVDEC/CUDA, com fallback para CPU em caso de falha; `--decode gpu` exige GPU compatível; `--decode cpu` força a CPU.
- `--rescan`: ignora a análise audiovisual armazenada e roda a análise novamente. Use junto de `--force` se a timeline desse modo já existir.
- `--encoder auto` tenta NVENC da NVIDIA e, se indisponível, usa `libx264` na CPU. Para forçar: `--encoder cpu`.
- `--quality high` é o novo padrão; use `--quality ultra` para priorizar ainda mais a qualidade.
- `--terminal` mantém a renderização no console; `--ui` abre explicitamente o painel visual (padrão automático no Windows).
- `--force` autoriza sobrescrever *os arquivos de saída gerados*, nunca o vídeo original. Sem essa opção, arquivos existentes são protegidos.

Para analisar novamente o mesmo modo alterando sua sensibilidade, use `--force` ou outra pasta; o cache audiovisual é reutilizado se o vídeo e a frequência de amostragem forem os mesmos.

### Como acompanhar a análise e a renderização

A Alpha 0.3 mantém as barras no terminal e adiciona o painel visual para renderização. O **percentual geral do painel é uma estimativa ponderada** (88% codificação dos cortes, 10% junção, 2% validação/finalização), não a porcentagem de bytes escritos no disco. O ETA depende da velocidade observada e pode variar bastante; o `+faststart` pode consumir tempo extra mesmo após a barra chegar perto de 100%.

### Teste específico da GPU sem perder o cache antigo

Para verificar se NVDEC está funcional na instalação Windows, utilize `--decode auto` em um **vídeo curto** e uma nova pasta de saída. O terminal informará `NVDEC/CUDA ativada` ou `NVDEC indisponível; usando CPU`.

**Importante:** se existir `analise.json` compatível, o editor **não analisará novamente** e não acionará NVDEC. Para medir um ganho de velocidade da GPU é necessário repetir a varredura com `--rescan` e comparar tempos com `--decode cpu` no mesmo trecho, usando pastas de saída separadas.

## O que esta Alpha ainda NÃO faz

- Não reconhece narrativamente GTA 6, bosses, piadas, objetivos ou reações. Usa apenas sinais acústicos e visuais.
- Não transcreve nem gera legendas nesta versão. A futura integração local com Faster-Whisper pode reaproveitar o que já fizemos no AI Shorts Generator.
- O painel gráfico atual é um **monitor de renderização**, não um editor visual. Ainda não possui trilha musical nova, transições, detecção sofisticada de cenas ou uma timeline visual editável.
- Não faz correção de cor HDR → SDR. **Para os primeiros testes, use gravações SDR**: vídeos HDR do PS5 podem sair com cores incorretas quando convertidos para H.264 8-bit.
- Usa somente a primeira faixa de áudio da gravação; não mistura múltiplas faixas separadas do OBS.
- Não garante que todos os trechos interessantes sejam escolhidos. Sempre revise a timeline antes de publicar.

## Privacidade e limites

- Todo processamento ocorre no computador que executa o programa, usando FFmpeg local.
- Nenhum vídeo é enviado a servidor, e o programa não solicita credenciais.
- Não existe limite artificial de 2h, nem de tamanho do vídeo final. O tempo de processamento e a necessidade de espaço em disco aumentam com a duração e quantidade de cortes.
- A análise é sequencial e em pequenos blocos, sem carregar o vídeo inteiro na memória. Decodificação via NVDEC não significa que todos os cálculos estejam rodando na GPU.
- A qualidade final é H.264/AAC MP4, respeitando o formato horizontal original. O renderizador reencoda os trechos para cortes precisos, podendo levar mais tempo que uma junção sem reencode.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Inclui testes de planejamento e integração, que geram vídeos sintéticos usando o FFmpeg. Os testes locais provaram a execução técnica em vídeos curtos; **ainda precisamos validar a qualidade editorial em gravações reais longas**.

## Próximas fases

1. Calibrar os dois modos com gravações reais de GTA 6, Final Fantasy, Resident Evil e outros jogos.
2. Reaproveitar (sem alterar o outro repositório) a transcrição local via Faster-Whisper para proteger diálogos e melhorar o ranking.
3. Ampliar a análise executada realmente na GPU e comparar desempenho/qualidade com a implementação CPU.
4. Adicionar classificação contextual com modelo multimodal local otimizado para RTX 4060 de 8 GB e 16 GB RAM, com cache e análise seletiva de frames.
5. Criar uma interface gráfica com pré-visualização e edição da timeline; posteriormente, gerar projetos interoperáveis com editores de vídeo quando houver adaptador compatível.

---

Projeto de João Victor Bonfim de Oliveira — AI Gameplay Editor Alpha 0.3.
