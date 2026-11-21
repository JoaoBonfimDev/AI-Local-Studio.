# AI Local Studio

**Uma suíte de ferramentas inteligentes para edição automatizada de gameplays, geração de Shorts e criação de vídeos de melhores momentos.**

Desenvolvido em Python, o **AI Local Studio** reúne três projetos independentes que utilizam análise audiovisual, processamento local e aceleração por GPU para facilitar a produção de conteúdo de jogos.

O principal objetivo é automatizar etapas trabalhosas da edição de vídeos, permitindo que criadores de conteúdo dediquem mais tempo às gravações e menos tempo à edição manual.

**100% local | Sem APIs pagas obrigatórias | Aceleração NVIDIA CUDA/NVENC**

---

## Os três projetos

### 1. AI Shorts Generator — Local Studio 1.1

Ferramenta desenvolvida para identificar momentos interessantes em gravações de gameplay e transformá-los automaticamente em vídeos verticais.

**Principais funcionalidades:**

- Geração de até 4 Shorts por execução.
- Análise de movimentação, áudio e falas.
- Classificação de momentos de ação, comentários e observações.
- Seleção de trechos com pontuação de relevância.
- Transcrição local utilizando Faster-Whisper.
- Suporte a aceleração CUDA em GPUs NVIDIA.
- Renderização vertical em 1080 × 1920.
- Legendas automáticas.
- Interface local acessível pelo navegador.
- Pré-visualização dos resultados.

**Ideal para:** YouTube Shorts, Instagram Reels e TikTok.

[Ver projeto AI Shorts Generator](./AI_Local_Studio_3_Projetos_1_0/AI_Shorts_Generator_1_1/)

### 2. AI Gameplay Editor — Alpha 0.3

Editor automatizado voltado para gravações longas de gameplay, permitindo reduzir trechos desnecessários e produzir vídeos organizados.

**Principais funcionalidades:**

- Edição de gameplays completas.
- Seleção automática de melhores momentos.
- Análise audiovisual.
- Remoção de períodos identificados como pouco relevantes.
- Organização cronológica dos cortes.
- Renderização com aceleração NVIDIA NVENC.
- Perfis de exportação com qualidade elevada.
- Progresso visual da renderização no navegador.
- Suporte a gravações de longa duração.

**Ideal para:** vídeos completos, séries de gameplay e melhores momentos para YouTube.

[Ver projeto AI Gameplay Editor](./AI_Local_Studio_3_Projetos_1_0/AI_Gameplay_Editor_0_3/)

### 3. AI Highlights Generator — 1.0

Ferramenta especializada em transformar gravações longas em uma sequência de vídeos horizontais de melhores momentos, preservando a apresentação original do jogo.

**Principais funcionalidades:**

- Geração de até 10 vídeos por execução.
- Duração desejada de 10 a 15 minutos por vídeo.
- Seleção de momentos relevantes da gameplay.
- Organização cronológica dos acontecimentos.
- Redução de repetições entre episódios.
- Preservação do áudio original.
- Nenhuma legenda, música ou efeito adicional.
- Preservação do enquadramento e proporção originais.
- Processamento local com FFmpeg.
- Interface visual no navegador.

A quantidade de episódios depende do conteúdo disponível. O sistema não precisa gerar dez vídeos quando não houver material suficiente.

**Ideal para:** séries de melhores momentos, vídeos de gameplay e conteúdo de longa duração para YouTube.

[Ver projeto AI Highlights Generator](./AI_Local_Studio_3_Projetos_1_0/AI_Highlights_Generator_1_0/)

---

## Tecnologias utilizadas

O conjunto dos projetos utiliza tecnologias como:

| Tecnologia | Aplicação |
|---|---|
| Python | Desenvolvimento e automação |
| FFmpeg / FFprobe | Análise, conversão, cortes e renderização |
| OpenCV | Processamento e análise visual |
| Faster-Whisper | Transcrição automática de áudio |
| CTranslate2 | Execução otimizada de modelos de transcrição |
| NVIDIA CUDA | Aceleração de tarefas compatíveis na GPU |
| NVIDIA NVDEC | Decodificação acelerada de vídeo |
| NVIDIA NVENC | Codificação acelerada de vídeo |
| HTML, CSS e JavaScript | Interfaces locais no navegador |
| Git e GitHub | Versionamento e distribuição |

A utilização dessas tecnologias varia conforme o projeto e a configuração do computador.

## Estrutura do repositório

```text
AI-Local-Studio/
│
├── README.md
├── .gitignore
│
└── AI_Local_Studio_3_Projetos_1_0/
    │
    ├── AI_Shorts_Generator_1_1/
    │   ├── aishorts/
    │   ├── assets/
    │   ├── docs/
    │   ├── tests/
    │   └── main.py
    │
    ├── AI_Gameplay_Editor_0_3/
    │   ├── gameplay_editor/
    │   ├── tests/
    │   └── main.py
    │
    ├── AI_Highlights_Generator_1_0/
    │   ├── highlights/
    │   ├── web/
    │   ├── tests/
    │   ├── INSTALAR.cmd
    │   ├── INICIAR.cmd
    │   └── main.py
    │
    ├── LEIA_PRIMEIRO.md
    ├── INSTALAR_HIGHLIGHTS.cmd
    └── INICIAR_HIGHLIGHTS.cmd
```

Os três aplicativos possuem código e documentação próprios, permitindo evolução independente.

## Requisitos

- Windows 10 ou 11.
- Python compatível com as dependências de cada projeto.
- FFmpeg e FFprobe.
- Espaço em disco para gravações e arquivos temporários.
- GPU NVIDIA compatível, recomendada para aceleração.

**Hardware utilizado durante o desenvolvimento:**

- Processador: AMD Ryzen 7 5700X.
- Placa de vídeo: NVIDIA GeForce RTX 4060 8 GB.
- Memória RAM: 16 GB DDR4.

O desempenho depende da duração, resolução e complexidade das gravações.

## Instalação e execução

Clone o repositório:

```powershell
git clone https://github.com/JoaoBonfimDev/AI-Local-Studio..git
```

Entre na pasta do projeto desejado.

**AI Shorts Generator:**

```powershell
cd AI-Local-Studio\AI_Local_Studio_3_Projetos_1_0\AI_Shorts_Generator_1_1

.\Instalar.cmd
.\Executar.cmd
```

**AI Gameplay Editor:**

```powershell
cd AI-Local-Studio\AI_Local_Studio_3_Projetos_1_0\AI_Gameplay_Editor_0_3

python main.py doctor
```

Consulte o README próprio do Gameplay Editor para os comandos de análise e renderização.

**AI Highlights Generator:**

```powershell
cd AI-Local-Studio\AI_Local_Studio_3_Projetos_1_0\AI_Highlights_Generator_1_0

.\INSTALAR.cmd
.\INICIAR.cmd
```

Execute os comandos de cada projeto a partir de seu respectivo diretório. Para instruções mais detalhadas, consulte os arquivos README individuais.

## Processamento local e privacidade

O AI Local Studio foi desenvolvido para executar o processamento das gravações no próprio computador.

Os vídeos não precisam ser enviados para serviços externos de edição ou transcrição.

Modelos locais podem exigir downloads durante a configuração inicial. Depois de instalados, os componentes compatíveis podem operar sem APIs pagas.

O projeto não exige uma conta de serviço de IA para processar os vídeos.

## Estado de desenvolvimento

O AI Local Studio está em evolução.

A seleção automática utiliza técnicas de análise audiovisual, classificação heurística e, quando disponível, modelos locais de transcrição.

Esses recursos não garantem compreensão completa de acontecimentos complexos, como humor, narrativa ou importância emocional de uma cena.

As melhorias planejadas incluem:

- Modelos multimodais locais.
- Seleção contextual mais precisa.
- Otimizações de desempenho na GPU.
- Melhor identificação de comentários do criador.
- Aprimoramentos das interfaces de edição.
- Melhorias na organização e revisão dos cortes.

## Sobre o projeto

O AI Local Studio nasceu da necessidade de automatizar a edição de gravações longas de videogames, utilizando ferramentas acessíveis e sem dependência de APIs pagas.

Além de seu uso na criação de conteúdo, o projeto representa uma experiência prática em desenvolvimento Python, processamento audiovisual, automação, integração de tecnologias e otimização de aplicações locais.

## Desenvolvedor

**João Victor Bonfim de Oliveira**

Desenvolvedor em formação, com foco em Python, análise de dados, automação e aplicações de inteligência artificial.

GitHub: [@JoaoBonfimDev](https://github.com/JoaoBonfimDev)

---

**AI Local Studio — Transformando gameplays em conteúdo com automação e inteligência artificial local.**