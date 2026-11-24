# GPU, CUDA e compatibilidade Python

## Componentes independentes

| Recurso | Verificação | Fallback |
| --- | --- | --- |
| H.264 NVENC | Codificação real 640×360, não apenas lista de encoders | Automático usa libx264; Exigir NVENC informa erro |
| NVDEC + scale CUDA | Decodificação/redução do bloco real da fonte | CPU para análise visual |
| Faster-Whisper CUDA | Carregar modelo local e executar transcrição | Automático usa CPU INT8; CUDA obrigatório informa erro |
| Telemetria GPU | nvidia-smi | Dados indisponíveis, sem números inventados |
| CPU/RAM | psutil opcional | Dados indisponíveis |

O teste NVENC usa dimensões acima do mínimo suportado: uma amostra 128×128 pode falhar mesmo com a RTX funcionando. A pontuação visual é calculada na CPU após reduzir os frames; somente decodificação/redução compatíveis usam CUDA. Não há promessa de acelerar toda a aplicação.

## Instalação

INSTALAR.cmd cria `.venv` com o Python que o iniciou e tenta instalar `requirements.txt` com `--only-binary=:all:`. INSTALAR_IA.cmd permite tentar novamente. Não compila automaticamente CTranslate2, PyAV ou ONNX para resolver uma wheel ausente. Falhas são mostradas no terminal e o núcleo audiovisual permanece utilizável sem fala.

O núcleo funciona com Python 3.14.7, validado nesta entrega. A disponibilidade de wheels Faster-Whisper/CTranslate2 e dependências transitivas varia com Python e plataforma. **A instalação de Whisper em 3.14.7 não foi validada neste ambiente.** Se a resolução falhar por falta de wheel e não por rede, instale Python 3.13 e crie uma instalação nova da pasta usando esse interpretador. Não copie uma `.venv` de outro projeto nem substitua o ambiente que já funciona.

Use o driver NVIDIA já instalado e mantenha suas bibliotecas CUDA 12/cuBLAS/cuDNN 9 configuradas conforme a versão real do CTranslate2 instalado. O Studio procura DLLs nos diretórios CUDA_PATH/CUDNN_PATH e nos diretórios `nvidia/*/bin` de sua própria instalação. Ele não reinstala drivers nem altera o PATH global. Bibliotecas existentes em outra `.venv` não são automaticamente parte desta.

## Modelo local

Selecione uma pasta convertida para Faster-Whisper com `model.bin`, `config.json` e arquivos do tokenizer. Uma pasta de modelos PyTorch comum não é equivalente. O botão Baixar modelo busca o modelo gratuito Systran/faster-whisper escolhido; esta é uma ação explícita de download, separada da análise.

Comece com `small`, CUDA automática, FP16, lote 1 e VAD ligado. Lotes 2 ou 4 podem aumentar a VRAM e só são utilizados quando a biblioteca instalada suporta BatchedInferencePipeline. INT8/FP16 é opcional. Não carregamos grandes modelos visuais ou um segundo Whisper junto ao primeiro. O processo de fala encerra antes de renderizar, liberando a memória GPU do modelo.

Na RTX 4060 8 GB com 16 GB de RAM, evite jogos pesados ou outros modelos consumindo VRAM durante a transcrição. Isso é uma orientação de uso, não uma alteração das configurações do computador pelo aplicativo.

## O que foi confirmado

NVENC e NVDEC/scale CUDA foram executados na RTX 4060 presente no ambiente de teste. Faster-Whisper e CTranslate2 não estavam instalados no Python acessível. Portanto, FP16, INT8/FP16, lotes e fallback real de Whisper estão implementados, mas aguardam teste com um modelo local. DIAGNOSTICO.cmd exibe o diagnóstico da instalação atual; ele não declara transcrição validada apenas porque detectou uma GPU.

Para verificar inferência de fala de verdade com um modelo existente, execute **TESTAR_IA.cmd**. O teste gera fala sintética offline e informa se CUDA ou CPU foi utilizado; não foi executado no ambiente desta entrega.
