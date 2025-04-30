from discord.ext import commands
import discord
import os
from dotenv import load_dotenv

from eventos import aniversarios, pasta, audit_log
from dados import salvar
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
        bot.loop.create_task(aniversarios.verificar_diariamente(bot))
        bot.loop.create_task(pasta.monitorar_pasta(bot))
        bot.loop.create_task(audit_log.monitorar_audit_log(bot))
    except Exception as e:
        print(f"⚠️ Erro ao iniciar tarefas: {e}")

@bot.event
async def on_guild_join(guild):
    salvar.salvar_dados()

@bot.event
async def on_guild_remove(guild):
    salvar.remover_guild(guild.id)

@bot.event
async def on_command_completion(ctx):
    salvar.salvar_dados()

# Carga inicial
salvar.carregar_tipos_mensagem()
salvar.carregar_dados()

# Carrega comandos
bot.load_extension("comandos.aniversarios")
bot.load_extension("comandos.cargos")
bot.load_extension("comandos.mensagens")
bot.load_extension("comandos.sugestoes")

from lockfile import criar_lockfile, remover_lockfile
import asyncio

async def main():
    salvar.carregar_tipos_mensagem()
    salvar.carregar_dados()
    criar_lockfile()
    import atexit
    atexit.register(remover_lockfile)

    await bot.load_extension("comandos.aniversarios")
    await bot.load_extension("comandos.cargos")
    await bot.load_extension("comandos.mensagens")
    await bot.load_extension("comandos.sugestoes")

    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)

if __name__ == \"__main__\":
    asyncio.run(main())
