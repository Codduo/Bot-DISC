import discord
from discord.ext import commands, tasks
import os
import asyncio
import logging
import json
import atexit
from dotenv import load_dotenv

from Comandos.comandos_basicos import setup as setup_basicos
from Comandos.aniversario import setup as setup_aniversario
from Comandos.ticket import setup as setup_ticket
from Comandos.reclamacao import setup as setup_reclamacao

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

LOCKFILE = "/tmp/bot_bmz.lock"

def remove_lockfile():
    if os.path.exists(LOCKFILE):
        os.remove(LOCKFILE)

atexit.register(remove_lockfile)

if os.path.exists(LOCKFILE):
    print("⚠️ Já existe uma instância do bot rodando. Abortando.")
    import sys
    sys.exit(1)

with open(LOCKFILE, "w") as f:
    f.write(str(os.getpid()))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

dados_globais = {
    "auto_roles": {},
    "ticket_response_channels": {},
    "mention_roles": {},
    "sugestao_channels": {},
    "test_channels": {},
    "mensagem_roles": {},
    "cargo_autorizado_mensagem": {},
}

def salvar_dados():
    temp_file = "dados_servidor_temp.json"
    final_file = "dados_servidor.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(dados_globais, f, indent=4, ensure_ascii=False)
    os.replace(temp_file, final_file)

def carregar_dados():
    if os.path.exists("dados_servidor.json"):
        with open("dados_servidor.json", "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            if conteudo:
                dados = json.loads(conteudo)
                for key, value in dados.items():
                    dados_globais[key] = value

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    
    try:
        bot.loop.create_task(verificar_diariamente())
    except Exception as e:
        print(f"⚠️ Erro ao iniciar tarefas: {e}")

@bot.event
async def on_command_completion(ctx):
    salvar_dados()

@bot.event
async def on_guild_join(guild):
    salvar_dados()

@bot.event
async def on_guild_remove(guild):
    guild_id = str(guild.id)
    for key in dados_globais.keys():
        if guild_id in dados_globais[key]:
            dados_globais[key].pop(guild_id, None)
    salvar_dados()

async def verificar_diariamente():
    while True:
        await asyncio.sleep(60)

def main():
    load_dotenv()
    carregar_dados()
    
    setup_basicos(bot, dados_globais)
    setup_aniversario(bot, dados_globais)
    setup_ticket(bot, dados_globais)
    setup_reclamacao(bot, dados_globais)
    setup_mensagens(bot, dados_globais)

    
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()