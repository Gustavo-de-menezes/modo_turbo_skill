# Guia do Modo Turbo (Alexa + Ollama + ngrok)

Referência rápida para operar o assistente de voz que roda no seu PC.

## 1. Visão geral

```
Alexa  →  ngrok (HTTPS)  →  servidor Flask (porta 5000)  →  Ollama (porta 11434)  →  modelo na GPU
```

| Peça | O que faz | Onde fica |
|---|---|---|
| Skill Alexa "modo turbo" | Recebe a voz e manda o texto ao seu PC | Alexa Developer Console |
| ngrok | Cria o endereço HTTPS público que aponta para o seu PC | Programa instalado |
| Servidor Flask | Recebe a pergunta, guarda a memória e chama o modelo | `C:\AlexaIA\servidor_alexa.py` |
| Ollama | Roda o modelo de IA | Programa instalado (sobe com o Windows) |
| Modelo | O "cérebro" (atual: `qwen3.5:4b`) | Pasta do Ollama (ver seção 9) |

**Arquivos importantes em `C:\AlexaIA`:**

| Arquivo | Função |
|---|---|
| `servidor_alexa.py` | Código do servidor |
| `historico.json` | Memória das conversas |
| `servidor.log` | Log do servidor (o que foi perguntado/respondido, erros) |
| `ngrok.log` | Log do túnel ngrok |

**Seu domínio fixo do ngrok:** `SEU-DOMINIO.ngrok-free.dev`
**Endpoint da skill:** `https://SEU-DOMINIO.ngrok-free.dev/alexa`

**Limite da Alexa:** a skill tem cerca de 8 segundos para responder. Esse tempo é fixo e não pode ser aumentado.

---

## 2. Como iniciar tudo

### Automático (ao ligar o PC)

O arquivo `modo_turbo.vbs` na pasta de inicialização do Windows sobe o servidor e o ngrok ocultos, sem janelas. O Ollama sobe sozinho com o Windows. Depois de ligar o PC e entrar na conta, espere cerca de 1 minuto.

Pré-requisitos: estar logado no Windows e o PC não entrar em suspensão (Configurações > Sistema > Energia > suspensão "Nunca" na tomada).

### Manual (sem reiniciar o PC)

```powershell
Start-Process wscript.exe "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\modo_turbo.vbs"
```

Ou abra `shell:startup` (Win + R) e dê duplo clique em `modo_turbo.vbs`.

### Como confirmar que subiu

1. `Get-Content C:\AlexaIA\servidor.log -Tail 20` deve mostrar `[MODELO CARREGADO NA GPU]`.
2. `Get-Content C:\AlexaIA\ngrok.log -Tail 20` deve mostrar o túnel online.
3. `ollama ps` deve listar o modelo com `100% GPU` e `UNTIL: Forever`.
4. Diga: "Alexa, abrir modo turbo".

---

## 3. Como parar tudo

### Parar o servidor e o ngrok

```powershell
taskkill /F /IM ngrok.exe
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*servidor_alexa*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

O segundo comando encerra só o servidor da Alexa, sem derrubar outros programas Python.

### Descarregar o modelo da GPU (libera a memória de vídeo)

```powershell
ollama stop qwen3.5:4b
```

### Fechar o Ollama por completo (opcional)

Clique com o botão direito no ícone do Ollama na bandeja do sistema (perto do relógio) e escolha **Quit**.

---

## 4. Como desativar o início automático

### Desativar o Modo Turbo (servidor + ngrok)

```powershell
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\modo_turbo.vbs"
```

Ou abra `shell:startup` e apague o arquivo `modo_turbo.vbs` manualmente.

### Desativar o Ollama na inicialização

Gerenciador de Tarefas (Ctrl + Shift + Esc) > aba **Inicializar** > clique em **Ollama** > **Desabilitar**.

### Reativar o Modo Turbo depois

Troque a linha do domínio se ele mudar, e rode:

```powershell
$pasta = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
@'
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\AlexaIA"
sh.Run "cmd /c python -u C:\AlexaIA\servidor_alexa.py > C:\AlexaIA\servidor.log 2>&1", 0, False
sh.Run "cmd /c ngrok http 5000 --url=https://SEU-DOMINIO.ngrok-free.dev --log=stdout > C:\AlexaIA\ngrok.log 2>&1", 0, False
'@ | Out-File -FilePath "$pasta\modo_turbo.vbs" -Encoding ascii
```

---

## 5. Como visualizar os processos em segundo plano

Como tudo roda oculto, use estes comandos:

```powershell
# Processos principais
Get-Process python, ngrok, ollama* -ErrorAction SilentlyContinue

# Só o servidor da Alexa (mostra a linha de comando)
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*servidor_alexa*" } | Select-Object ProcessId, Name, CommandLine

# A porta 5000 está em uso? (servidor rodando)
netstat -ano | findstr :5000

# Modelo carregado na memória
ollama ps

# Acompanhar o log do servidor em tempo real (Ctrl+C para sair)
Get-Content C:\AlexaIA\servidor.log -Tail 30 -Wait
```

Também dá para ver pelo Gerenciador de Tarefas (Ctrl + Shift + Esc), aba **Detalhes**: procure `python.exe`, `ngrok.exe` e `ollama.exe`.

---

## 6. Como trocar de modelo

### Passo a passo

1. Baixar o novo modelo:
   ```powershell
   ollama pull NOME_DO_MODELO
   ```
2. Testar rápido no terminal, com métricas de velocidade (veja `eval rate` e `total duration`):
   ```powershell
   ollama run NOME_DO_MODELO --verbose "Explique em duas frases curtas o que é lactase."
   ```
   Para modelos com raciocínio (Qwen3, Qwen3.5, Gemma 4), use `--think=false`.
3. Trocar o nome no script:
   ```powershell
   (Get-Content C:\AlexaIA\servidor_alexa.py -Encoding utf8) -replace 'MODELO = ".*?"', 'MODELO = "NOME_DO_MODELO"' | Set-Content C:\AlexaIA\servidor_alexa.py -Encoding utf8
   ```
4. Descarregar o modelo antigo:
   ```powershell
   ollama stop NOME_DO_MODELO_ANTIGO
   ```
5. Reiniciar o servidor (seção 3 para parar, seção 2 para iniciar).
6. Conferir com `ollama ps`: o ideal é **100% GPU**. Se aparecer divisão CPU/GPU, o modelo é grande demais para a placa e ficará lento.

### Modelos já testados

| Modelo | Resultado |
|---|---|
| `qwen3.5:4b` | Em uso. Cabe na GPU e responde em cerca de 1,5 s com o raciocínio desligado |
| `llama3.1:8b` | Não cabe inteiro na GTX 1660 (parte roda no processador); mais lento |
| `llama3.2:3b` | Rápido, mas o português e a precisão foram piores |
| `gemma4:e4b` | Boa qualidade, mas com raciocínio ligado gerou muito texto de "pensamento" |

### Atenção com modelos de raciocínio

Qwen3, Qwen3.5 e Gemma 4 podem "pensar" antes de responder. O script já envia `"think": False` e remove blocos `<think>`. Se um modelo novo responder vazio ou muito devagar, é quase sempre isso.

### Apagar um modelo do disco

```powershell
ollama list
ollama rm NOME_DO_MODELO
```

---

## 7. Como alterar o script

Arquivo: `C:\AlexaIA\servidor_alexa.py`

1. Faça um backup antes:
   ```powershell
   Copy-Item C:\AlexaIA\servidor_alexa.py C:\AlexaIA\servidor_alexa.bak.py
   ```
2. Abra para editar:
   ```powershell
   notepad C:\AlexaIA\servidor_alexa.py
   ```
3. Salve (Ctrl + S) e **reinicie o servidor** (pare e inicie de novo). O Python só lê o arquivo ao iniciar.

### Parâmetros mais usados (no topo do arquivo)

| Variável | O que controla | Observação |
|---|---|---|
| `MODELO` | Modelo usado | Nome exato do `ollama list` |
| `MAX_MENSAGENS` | Quantas mensagens recentes o modelo vê | Menos = mais rápido; mais = lembra mais |
| `TIMEOUT_OLLAMA` | Tempo máximo esperando o modelo (segundos) | Não passe de ~7,5 por causa do limite da Alexa |
| `SYSTEM_PROMPT` | Personalidade e regras da resposta | Mantenha "sem markdown", pois o texto é falado |
| `num_predict` (dentro do `payload`) | Tamanho máximo da resposta, em tokens | Maior = respostas mais longas e lentas |

### Memória das conversas

- Falar "nova conversa" ou "esquece tudo" na Alexa apaga a memória.
- Ou apague o arquivo manualmente com o servidor parado: `Remove-Item C:\AlexaIA\historico.json`.

### Se alterar frases ou intents da skill

Isso é feito no JSON do modelo de interação (Alexa Developer Console > Build > JSON Editor). Depois de colar, clique em **Save Model** e **Build Model**.

---

## 8. Como configurar o ngrok

### Instalação e autenticação (uma vez só)

1. Instale em https://ngrok.com/download e confirme com `ngrok version`.
2. Crie a conta gratuita em https://dashboard.ngrok.com.
3. No painel, abra **Your Authtoken**, copie o token e rode:
   ```powershell
   ngrok config add-authtoken SEU_TOKEN
   ```

### Domínio fixo

- Fica em https://dashboard.ngrok.com/domains. Contas gratuitas têm 1 domínio fixo (o seu é `SEU-DOMINIO.ngrok-free.dev`).
- Comando que sobe o túnel:
  ```powershell
  ngrok http 5000 --url=https://SEU-DOMINIO.ngrok-free.dev
  ```

### Endpoint da skill

Alexa Developer Console > sua skill > **Endpoint**:

- Tipo: **HTTPS**
- Default Region: `https://SEU-DOMINIO.ngrok-free.dev/alexa`
- Certificado: "My development endpoint is a sub-domain of a domain that has a wildcard certificate from a certificate authority"

Salve e faça o Build.

### Observações

- O endereço é público: não compartilhe o link.
- Se mudar de conta ou domínio, atualize o `.vbs` (seção 4) e o Endpoint da skill.
- Se o `ngrok.log` disser que o domínio não existe, ele ainda não foi reservado no painel.

---

## 9. Onde estão os modelos baixados

Pasta padrão do Ollama no Windows:

```
%USERPROFILE%\.ollama\models
```

Para abrir no Explorer:

```powershell
explorer "$env:USERPROFILE\.ollama\models"
```

- Cada modelo tem de 2 a 6 GB. Para listar e ver o tamanho de cada um: `ollama list`.
- Para liberar espaço, use `ollama rm NOME` em vez de apagar arquivos à mão.
- Para mover os modelos para outro disco, defina a variável de ambiente `OLLAMA_MODELS` com a nova pasta (Configurações do Windows > Variáveis de ambiente) e reinicie o Ollama.

---

## 10. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Alexa diz que não conseguiu acessar a skill | Servidor ou ngrok parados, ou endpoint errado | Confira `ngrok.log` e `servidor.log` (seção 5) e o Endpoint da skill |
| "Meu cérebro local demorou muito" | Modelo ainda carregando ou lento | Pergunte de novo; veja `ollama ps` (deve ser 100% GPU) |
| Alexa fica muda / resposta vazia | Modelo de raciocínio gastou os tokens pensando | Confirme `"think": False` no script |
| Log mostra porta 5000 em uso | Instância antiga do servidor ainda rodando | Pare tudo (seção 3) e inicie de novo |
| `python` ou `ngrok` não encontrado ao subir sozinho | Caminho não está disponível no início do Windows | Use o caminho completo no `.vbs` (descubra com `where python` e `where ngrok`) |
| Nada sobe depois de reiniciar | Windows parou na tela de senha, ou PC suspendeu | Faça login; desative a suspensão |

### Limites a lembrar

- Modelos pequenos (4B) erram fatos e podem inventar nomes, números e preços com muita confiança. Para saúde, remédios e dados importantes, confirme com uma fonte confiável ou profissional.
- Falar "pesquise ..." faz o servidor buscar na internet antes de responder, o que reduz erros de fatos, mas soma 1 a 3 segundos.
