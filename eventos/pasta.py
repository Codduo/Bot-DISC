import os
import asyncio
from datetime import datetime
from config import CAMINHO_PASTA, SEU_CANAL_ID, TEMPO_ESPERA_CONFIRMACAO
from eventos.audit_log import ultimos_eventos

arquivos_anteriores = set()

async def confirmar_estabilidade(arquivo):
    try:
        mod_time_inicial = os.stat(arquivo).st_mtime
    except FileNotFoundError:
        return False

    await asyncio.sleep(TEMPO_ESPERA_CONFIRMACAO)

    try:
        mod_time_final = os.stat(arquivo).st_mtime
    except FileNotFoundError:
        return False

    return mod_time_inicial == mod_time_final

async def monitorar_pasta(bot):
    global arquivos_anteriores

    def mapear_arquivos():
        arquivos = {}
        for raiz, _, encontrados in os.walk(CAMINHO_PASTA):
            for nome in encontrados:
                caminho = os.path.join(raiz, nome)
                try:
                    arquivos[caminho] = os.stat(caminho).st_mtime
                except FileNotFoundError:
                    continue
        return arquivos

    try:
        arquivos_anteriores = mapear_arquivos()
    except Exception as e:
        print(f"Erro inicial ao mapear arquivos: {e}")
        return

    await bot.wait_until_ready()
    canal = bot.get_channel(SEU_CANAL_ID)

    while True:
        await asyncio.sleep(5)
        try:
            arquivos_atuais = mapear_arquivos()
            novos = set(arquivos_atuais) - set(arquivos_anteriores)
            removidos = set(arquivos_anteriores) - set(arquivos_atuais)
            modificados = {
                arq for arq in arquivos_anteriores & arquivos_atuais
                if arquivos_anteriores[arq] != arquivos_atuais[arq]
            }

            for arquivo in novos:
                await enviar_mensagem(canal, arquivo, "Criou")

            for arquivo in removidos:
                await enviar_mensagem(canal, arquivo, "Deletou")

            for arquivo in modificados:
                await enviar_mensagem(canal, arquivo, "Alterou")

            arquivos_anteriores = arquivos_atuais
        except Exception as e:
            print(f"Erro ao monitorar a pasta: {e}")

async def enviar_mensagem(canal, caminho, acao):
    nome = os.path.relpath(caminho, CAMINHO_PASTA)
    info = ultimos_eventos.pop(nome, None)

    msg = (
        f"📄 **Usuário:** {info['usuario']}\n"
        f"🛠 **Alteração:** {info['acao']} `{nome}`\n"
        f"🕒 **Data:** {info['data']}"
    ) if info else (
        f"📄 **Usuário:** Desconhecido\n"
        f"🛠 **Alteração:** {acao} `{nome}`\n"
        f"🕒 **Data:** Desconhecida"
    )

    if canal and await confirmar_estabilidade(caminho):
        await canal.send(msg)
    else:
        print(f"⏳ Arquivo {nome} ainda instável ou canal indisponível")
