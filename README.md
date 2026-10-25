# Modo Turbo

Um assistente de voz para a Alexa que responde usando uma **IA rodando no seu próprio computador**, em vez de depender de um serviço de IA na nuvem.

Você fala com a Alexa, ela envia o texto da pergunta para o seu PC, um modelo de linguagem local gera a resposta e a Alexa a fala de volta, com memória da conversa e, quando pedido, pesquisa na internet.

---

## Sumário

1. [Como funciona](#como-funciona)
2. [Vantagens](#vantagens)
3. [Funcionalidades](#funcionalidades)
4. [Componentes](#componentes)
5. [Requisitos](#requisitos)
6. [Estrutura de arquivos](#estrutura-de-arquivos)
7. [Como usar por voz](#como-usar-por-voz)
8. [Instalação resumida](#instalação-resumida)
9. [Desempenho](#desempenho)
10. [Limitações](#limitações)
11. [Privacidade e segurança](#privacidade-e-segurança)
12. [Ideias para evoluir](#ideias-para-evoluir)

---

## Como funciona

```
 Você fala
    │
    ▼
┌─────────┐   texto da pergunta   ┌──────────────┐   HTTPS   ┌────────────────┐
│  Alexa  │ ────────────────────► │ Skill "modo  │ ────────► │  ngrok (túnel) │
│ (Echo)  │                       │    turbo"    │           └───────┬────────┘
└─────────┘                       └──────────────┘                   │
    ▲                                                                ▼
    │ resposta falada                                    ┌────────────────────┐
    │                                                    │ Servidor Flask     │
    │                                                    │ (porta 5000)       │
    │                                                    │ • histórico        │
    │                                                    │ • busca na web     │
    │                                                    └─────────┬──────────┘
    │                                                              │
    │                                                              ▼
    │                                                    ┌────────────────────┐
    └─────────────────────────────────────────────────── │ Ollama + modelo    │
                                                         │ (roda na GPU)      │
                                                         └────────────────────┘
```

### Passo a passo de uma pergunta

1. Você diz: "Alexa, abrir modo turbo" e depois, por exemplo, "me diga por que o céu é azul".
2. A Alexa converte a voz em texto (essa etapa acontece nos servidores da Amazon) e envia o texto para a skill.
3. A skill chama o endereço HTTPS fixo do ngrok, que encaminha a requisição para o servidor Flask no seu PC.
4. O servidor junta a pergunta com as últimas mensagens da conversa e envia tudo ao Ollama.
5. O modelo, carregado na GPU, gera uma resposta curta.
6. O servidor devolve o texto para a Alexa, que o fala em voz alta.

Tudo isso precisa acontecer em cerca de **8 segundos**, que é o limite fixo da Amazon para uma skill responder.

---

## Vantagens

- **A IA roda no seu computador.** O modelo é seu: sem mensalidade de API, sem cobrança por pergunta e sem limite de uso além do que o PC aguenta.
- **Controle total.** Você escolhe o modelo, a personalidade (o `SYSTEM_PROMPT`), o tamanho das respostas e o que fica guardado.
- **Memória da conversa.** A Alexa original não lembra do que você falou; aqui o servidor guarda as últimas trocas e as envia ao modelo, então perguntas de continuação funcionam ("e onde ele nasceu?").
- **Pesquisa na internet sob demanda.** Dizendo "pesquise ...", o servidor busca resultados e o modelo responde com base neles, o que reduz respostas inventadas sobre fatos.
- **Rápido para o hardware.** Com um modelo de 4B parâmetros inteiro na GPU, a geração leva cerca de 1 a 2 segundos, bem dentro do limite da Alexa.
- **Modelo sempre pronto.** O servidor carrega o modelo na GPU ao iniciar e o mantém na memória, evitando a demora da primeira pergunta.
- **Funciona sozinho.** Tudo sobe junto com o Windows, em segundo plano, sem janelas abertas, com logs gravados em arquivo.
- **Endereço fixo e gratuito.** O domínio estático do ngrok evita ter que reconfigurar a skill a cada reinício.
- **Aprendizado.** Um projeto pequeno e legível (um arquivo Python) para entender como integrar voz, IA local e uma API.

---

## Funcionalidades

| Recurso | Como acionar | O que faz |
|---|---|---|
| Perguntas gerais | "me diga ...", "explica ...", "o que é ...", "quem foi ..." | O modelo responde em até 2 frases curtas, em português, sem formatação |
| Pesquisa na web | "pesquise ...", "busque ...", "procure na internet ..." | Busca resultados (DuckDuckGo) e o modelo responde com base neles |
| Memória | Automática | Guarda as últimas mensagens por usuário em `historico.json` |
| Limpar memória | "nova conversa", "esquece tudo" | Apaga o histórico |
| Ajuda | "ajuda" | Explica os comandos |
| Encerrar | "parar", "tchau" | Fecha a skill |
| Aquecimento do modelo | Automático ao iniciar | Carrega o modelo na GPU antes da primeira pergunta |
| Proteção contra resposta vazia | Automática | Se o modelo não gerar texto, a Alexa avisa em vez de ficar muda |

---

## Componentes

| Componente | Função |
|---|---|
| **Skill Alexa** (invocação "modo turbo") | Define as frases que a Alexa entende e envia o texto ao seu endpoint |
| **ngrok** | Expõe o servidor local em um endereço HTTPS público e fixo (a Alexa só aceita HTTPS) |
| **Servidor Flask** (`servidor_alexa.py`) | Recebe as requisições, mantém a memória, faz a busca e chama o modelo |
| **Ollama** | Executa o modelo de linguagem localmente |
| **Modelo** (atual: `qwen3.5:4b`) | Gera as respostas |
| **DuckDuckGo (`ddgs`)** | Fornece resultados de busca sem necessidade de chave de API |

---

## Requisitos

### Hardware de referência

O projeto foi desenvolvido e testado neste computador:

| Componente | Especificação |
|---|---|
| GPU | NVIDIA GTX 1660, 6 GB de VRAM |
| Processador | Intel Core i5-9400F (6 núcleos) |
| Memória RAM | 16 GB |
| Armazenamento principal | SSD NVMe M.2 Kingston, 1 TB |
| Armazenamento secundário | SSD 2,5" de 120 GB |
| Armazenamento de dados | HD Seagate de 1 TB |

O fator que mais pesa é a **VRAM da GPU (6 GB)**:

- Modelos de até cerca de 4B parâmetros cabem inteiros na GPU e respondem rápido, dentro do limite de 8 segundos da Alexa.
- Modelos de 7 a 8B (como o `llama3.1:8b`) não cabem inteiros nessa placa: parte roda no processador e a resposta fica lenta demais.
- Os modelos ficam melhor no SSD NVMe, onde carregam mais rápido. O HD é lento demais para isso, e o SSD de 120 GB fica apertado, já que cada modelo ocupa de 2 a 6 GB.
- Para usar modelos maiores com mais qualidade, o upgrade que faria diferença é uma placa de vídeo com 12 GB ou mais de VRAM.

### Software e serviços

- Windows com PC ligado e sem entrar em suspensão
- GPU com cerca de 6 GB de VRAM (mínimo recomendado para o modelo de 4B usado aqui)
- [Ollama](https://ollama.com) instalado
- Python 3 com as bibliotecas `flask`, `requests` e `ddgs` (`pip install flask requests ddgs`)
- Conta gratuita no [ngrok](https://ngrok.com), com o domínio estático reservado
- Conta de desenvolvedor Alexa (gratuita) e um dispositivo com Alexa
- Conexão com a internet

---

## Estrutura de arquivos

```
C:\AlexaIA\
├── servidor_alexa.py   # código do servidor
├── historico.json      # memória das conversas (criado automaticamente)
├── servidor.log        # log do servidor
└── ngrok.log           # log do túnel

...\Startup\modo_turbo.vbs   # inicia servidor e ngrok ocultos ao ligar o Windows
```

---

## Como usar por voz

```
"Alexa, abrir modo turbo"
"me diga quem foi Santos Dumont"
"me diga onde ele nasceu"                  ← usa a memória da conversa
"pesquise notícias de hoje"                ← busca na internet
"nova conversa"                            ← apaga a memória
"parar"                                    ← encerra
```

---

## Instalação resumida

1. **Ollama:** instale e baixe o modelo: `ollama pull qwen3.5:4b`.
2. **Servidor:** salve o `servidor_alexa.py` em `C:\AlexaIA` e instale as bibliotecas.
3. **ngrok:** instale, rode `ngrok config add-authtoken SEU_TOKEN` e reserve o domínio gratuito em *Dashboard > Domains*.
4. **Skill Alexa:** crie uma skill personalizada no Alexa Developer Console, cole o JSON do modelo de interação, faça o *Build* e aponte o Endpoint para `https://SEU-DOMINIO/alexa`.
5. **Inicialização automática:** crie o `modo_turbo.vbs` na pasta `shell:startup` para subir o servidor e o ngrok em segundo plano.

Os comandos completos de cada etapa, além de como parar, trocar de modelo, editar o script e resolver problemas, estão em **`guia_modo_turbo.md`**.

---

## Desempenho

Com o `qwen3.5:4b` carregado 100% na GPU, no [hardware de referência](#hardware-de-referência) (GTX 1660 de 6 GB, i5-9400F, 16 GB de RAM, SSD NVMe):

- geração de cerca de 40 tokens por segundo;
- respostas curtas em torno de 1 a 2 segundos;
- primeira carga do modelo de cerca de 8 a 20 segundos, absorvida pelo aquecimento automático ao iniciar.

Modelos que não cabem inteiros na VRAM (como o `llama3.1:8b` nessa placa) rodam em parte no processador e ficam bem mais lentos. Confira sempre com `ollama ps`: o ideal é **100% GPU**.

---

## Limitações

- **Limite de 8 segundos da Alexa.** É fixo e não pode ser alterado. Respostas lentas resultam em erro.
- **Modelos pequenos erram fatos.** Um modelo de 4B parâmetros pode inventar nomes, datas, preços e informações com muita confiança. Para saúde, remédios, finanças e dados importantes, confirme com uma fonte confiável ou profissional. A pesquisa na web ajuda, mas não elimina o erro.
- **Reconhecimento de voz.** A transcrição é feita pela Amazon e pode errar nomes próprios e palavras em inglês; não há como corrigir o áudio.
- **O PC precisa estar ligado.** Se o computador estiver desligado, em suspensão ou sem internet, a skill não responde.
- **Respostas curtas.** O prompt limita a 2 frases para caber no tempo e soar bem em voz alta.
- **Servidor de desenvolvimento.** O Flask roda no modo de desenvolvimento, suficiente para uso doméstico, mas não é o ideal para produção.

---

## Privacidade e segurança

- **Áudio:** processado pela Amazon (como em qualquer skill da Alexa). O que chega ao seu PC é só o texto.
- **Respostas da IA:** geradas localmente; o texto da pergunta não é enviado a nenhum serviço de IA na nuvem.
- **Pesquisa na web:** ao usar "pesquise", o texto da pergunta é enviado ao DuckDuckGo para buscar resultados.
- **Histórico:** fica no arquivo `historico.json`, no seu PC, e pode ser apagado por voz ou manualmente.
- **Endereço público:** o domínio do ngrok é público. Não o compartilhe. O servidor atual **não valida a assinatura** das requisições da Alexa, então qualquer pessoa que conheça o endereço poderia enviar requisições a ele.

---

## Ideias para evoluir

- Validar a assinatura e o ID da skill nas requisições recebidas da Alexa.
- Busca automática para perguntas de fatos ("quem foi", "quando", "onde"), sem precisar dizer "pesquise".
- Resposta em segundo plano para perguntas demoradas, com um comando "resposta" para ouvir o resultado depois.
- Memória de longo prazo (fatos sobre o usuário) além das últimas trocas.
- Trocar o servidor de desenvolvimento por um servidor WSGI (por exemplo, Waitress).
- Comandos de voz para trocar de modelo ou mudar o estilo de resposta.
