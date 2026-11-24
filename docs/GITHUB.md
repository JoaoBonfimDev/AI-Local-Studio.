# Atualizar o repositório existente

Repositório informado: https://github.com/JoaoBonfimDev/AI-Local-Studio

O ZIP recebido continha os fontes, mas não forneceu um checkout Git utilizável. A consulta normal a GitHub falhou por DNS no ambiente. Por isso não foi criada uma branch a partir do remoto, não há commits novos sobre seu histórico e nenhum push/merge foi realizado. Não criamos um repositório substituto com histórico independente.

## Atualização em uma branch

Em um checkout local do seu repositório existente, primeiro confira as mudanças pessoais. Crie a branch **dev/ai-local-studio-2.0** a partir da base desejada. Copie para a raiz desse checkout os arquivos do pacote 2.0, mantendo a pasta `.git` e os projetos antigos existentes. Não remova as versões antigas durante a primeira revisão. README e .gitignore passam a apresentar o aplicativo integrado.

Exemplo para executar pessoalmente, quando o acesso à rede estiver disponível:

```powershell
git clone https://github.com/JoaoBonfimDev/AI-Local-Studio.git
cd AI-Local-Studio
git switch -c dev/ai-local-studio-2.0
# Copie os arquivos extraídos da versão 2.0 para esta pasta, preservando .git.
git status --short
# Revise as mudanças, rode TESTAR.cmd e só então selecione os arquivos desejados.
git add main.py INSTALAR.cmd INICIAR.cmd INSTALAR_IA.cmd TESTAR.cmd DIAGNOSTICO.cmd requirements.txt README.md .gitignore core modes render web tests scripts docs legacy
git diff --cached --stat
git commit -m "Integrate AI Local Studio 2.0"
```

Não há comando push/merge automatizado no pacote. Envie a branch somente quando você decidir autorizar a publicação. Não force push nem reescreva o histórico.

## Conteúdo ignorado

Não envie `.venv`, `.local`, `.render`, `.studio`, `tools`, gravações, modelos, relatórios de sessões privadas, saídas de vídeo ou configurações pessoais. A lista de arquivos em `docs/FONTES_AUDITADAS.json` contém caminhos relativos e hashes dos fontes de entrada; não contém gravações.
