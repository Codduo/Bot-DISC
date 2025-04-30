from discord.ext import commands
import discord
import os
from dotenv import load_dotenv

from eventos import aniversarios, pasta, audit_log
from dados import salvar, tipos_mensagem
from modelos.ticket import TicketButtonView
from modelos.sugestao import SugestaoView

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        bot.add_view(TicketButtonView())
        bot.add_view(SugestaoView())
        bot.loop.create_task(aniversarios.verificar_diariamente())
        bot.loop.create_task(pasta.monitorar_pasta())
        bot.loop.create_task(audit_log.monitorar_audit_log())
    except Exception as e:
        print(f"⚠️ Erro ao iniciar tarefas: {e}")

# Eventos extras de entrada/saída
@bot.event
async def on_guild_join(guild):
    salvar.salvar_dados()

@bot.event
async def on_guild_remove(guild):
    salvar.remover_guild(guild.id)

@bot.event
async def on_command_completion(ctx):
    salvar.salvar_dados()

# Carregamento de dados iniciais
salvar.carregar_dados()
tipos_mensagem.carregar_tipos_mensagem()

# Lockfile (evita múltiplas instâncias simultâneas)
from lockfile import criar_lockfile, remover_lockfile
criar_lockfile()
import atexit
atexit.register(remover_lockfile)

# Rodar bot
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
