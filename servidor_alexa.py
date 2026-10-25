import json
import os
import re
import time
import threading
from flask import Flask, request, jsonify
import requests
from ddgs import DDGS

app = Flask(__name__)
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
MODELO = "qwen3.5:4b"
MAX_MENSAGENS = 6  # últimas 3 trocas (pergunta + resposta)
TIMEOUT_OLLAMA = 7.5
ARQUIVO_HISTORICO = r"C:\AlexaIA\historico.json"

SYSTEM_PROMPT = (
    "Você é um assistente de voz integrado à Alexa chamado Modo Turbo. "
    "Responda em português do Brasil de forma direta, natural e concisa, em no máximo 2 frases curtas. "
    "Jamais use formatação markdown, asteriscos ou listas, pois seu texto será lido em voz alta. "
    "A pergunta vem de reconhecimento de voz e pode ter palavras erradas, principalmente nomes de produtos ou palavras em inglês. "
    "Se um nome parecer estranho ou você não tiver certeza de que ele existe, diga que não tem certeza e peça para repetir. "
    "Nunca invente nomes, preços ou informações sobre remédios."
)

# Carrega o histórico salvo (chave = userId da Alexa)
HISTORICO = {}
if os.path.exists(ARQUIVO_HISTORICO):
    try:
        with open(ARQUIVO_HISTORICO, encoding="utf-8") as f:
            HISTORICO = json.load(f)
    except Exception as e:
        print(f"Não consegui ler o histórico: {e}")
        HISTORICO = {}


def salvar_historico():
    try:
        with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(HISTORICO, f, ensure_ascii=False)
    except Exception as e:
        print(f"Não consegui salvar o histórico: {e}")


def aquecer_modelo():
    """Carrega o modelo na GPU assim que o servidor sobe (tenta por ~2,5 minutos)."""
    for _ in range(30):
        try:
            requests.post(
                OLLAMA_GENERATE_URL,
                json={"model": MODELO, "keep_alive": -1},
                timeout=120,
            )
            print("---> [MODELO CARREGADO NA GPU]")
            return
        except Exception:
            time.sleep(5)
    print("---> [NÃO CONSEGUI CARREGAR O MODELO]")


def buscar_web(consulta):
    try:
        resultados = DDGS(timeout=3).text(consulta, region="br-pt", max_results=3)
        return "\n".join(f"- {r['body'][:300]}" for r in resultados)
    except Exception as e:
        print(f"Erro na busca: {e}")
        return ""


def consultar_ollama(pergunta, user_id, usar_busca=False):
    msgs = HISTORICO.setdefault(user_id, [])
    msgs.append({"role": "user", "content": pergunta})
    contexto = [dict(m) for m in msgs[-MAX_MENSAGENS:]]

    # A busca vale só para esta pergunta e não é guardada no histórico
    if usar_busca:
        resultados = buscar_web(pergunta)
        if resultados:
            print(f"---> [RESULTADOS DA BUSCA]:\n{resultados}")
            contexto[-1]["content"] = (
                f"Resultados de busca na internet:\n{resultados}\n\n"
                f"Usando só esses resultados, responda: {pergunta}"
            )

    payload = {
        "model": MODELO,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + contexto,
        "stream": False,
        "think": False,
        "keep_alive": -1,
        "options": {"num_predict": 120, "temperature": 0.6}
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_OLLAMA)
        resposta = resp.json()["message"]["content"]
        resposta = re.sub(r"<think>.*?</think>", "", resposta, flags=re.S).strip()

        if not resposta:
            print("Resposta vazia do modelo.")
            msgs.pop()
            return "Não consegui formular a resposta. Pode repetir a pergunta?"

        msgs.append({"role": "assistant", "content": resposta})
        del msgs[:-MAX_MENSAGENS * 2]  # limita o tamanho guardado
        salvar_historico()
        return resposta
    except Exception as e:
        print(f"Erro no Ollama: {e}")
        msgs.pop()  # remove a pergunta que ficou sem resposta
        return "Meu cérebro local demorou muito para responder."


def montar_resposta_alexa(texto, encerrar_sessao=False):
    return jsonify({
        "version": "1.0",
        "response": {
            "outputSpeech": {"type": "PlainText", "text": texto},
            "reprompt": {"outputSpeech": {"type": "PlainText", "text": "Pode fazer outra pergunta, ou diga parar."}},
            "shouldEndSession": encerrar_sessao
        }
    })


@app.route("/alexa", methods=["POST"])
def webhook_alexa():
    dados = request.get_json()
    req = dados.get("request", {})
    tipo_req = req.get("type")
    user_id = dados.get("session", {}).get("user", {}).get("userId", "padrao")

    print(f"\n---> [EVENTO RECEBIDO DA AMAZON]: {tipo_req}")

    if tipo_req == "LaunchRequest":
        return montar_resposta_alexa("Modo turbo ligado na GTX 1660. Comece sua pergunta dizendo: me diga, ou, explica.")

    elif tipo_req == "IntentRequest":
        intent = req.get("intent", {})
        nome_intent = intent.get("name")
        slots = intent.get("slots", {})
        print(f"---> [INTENT IDENTIFICADA]: {nome_intent} | SLOTS: {slots}")

        if nome_intent == "LimparMemoriaIntent":
            HISTORICO[user_id] = []
            salvar_historico()
            return montar_resposta_alexa("Memória apagada. Pode começar uma nova conversa.")

        elif nome_intent in ["PerguntaIntent", "PesquisaIntent"]:
            pergunta = slots.get("query", {}).get("value", "")
            if not pergunta:
                return montar_resposta_alexa("Não escutei a pergunta. Comece dizendo: me diga, ou, pesquise, seguido da pergunta.")

            usar_busca = (nome_intent == "PesquisaIntent")
            print(f"---> [PERGUNTA PARA A IA] (busca={usar_busca}): {pergunta}")
            resposta_ia = consultar_ollama(pergunta, user_id, usar_busca)
            print(f"---> [RESPOSTA DA GTX 1660]: {resposta_ia}")
            return montar_resposta_alexa(resposta_ia, encerrar_sessao=False)

        elif nome_intent in ["AMAZON.StopIntent", "AMAZON.CancelIntent", "AMAZON.NoIntent", "AMAZON.NavigateHomeIntent"]:
            return montar_resposta_alexa("Desligando modo turbo. Até mais!", encerrar_sessao=True)

        elif nome_intent == "AMAZON.YesIntent":
            return montar_resposta_alexa("Pode falar! Comece dizendo: me diga, ou, explica.", encerrar_sessao=False)

        elif nome_intent == "AMAZON.HelpIntent":
            return montar_resposta_alexa("Diga: me diga, seguido da pergunta. Para buscar na internet, diga: pesquise. Para apagar a conversa, diga: nova conversa.", encerrar_sessao=False)

    elif tipo_req == "SessionEndedRequest":
        return jsonify({"version": "1.0"})

    return montar_resposta_alexa("Não entendi o formato. Comece a sua frase dizendo: me diga, ou, explica.")


if __name__ == "__main__":
    threading.Thread(target=aquecer_modelo, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
