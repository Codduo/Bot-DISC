import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configura intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

# Inicializa o bot
bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Importa e configura os módulos ─────────────────────────────────────────────

from aniversarios import setup_aniversarios_commands, verificar_diariamente
from mensagens import setup_mensagens_commands, carregar_tipos_mensagem
from cargos import setup_cargos_commands, carregar_dados_servidor
from tickets import setup_tickets_commands

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    await bot.change_presence(activity=discord.Game(name="gerenciando o servidor 🎛️"))
    
    # Views permanentes
    try:
        bot.add_view(TicketButtonView())
        bot.add_view(SugestaoView())
    except Exception as e:
        print(f"⚠️ Erro ao registrar views: {e}")
    
    # Inicia a tarefa de verificação diária de aniversários
    bot.loop.create_task(verificar_diariamente(bot))

# ─── Eventos adicionais globais ────────────────────────────────────────────────

@bot.event
async def on_command_completion(ctx):
    from cargos import salvar_dados_servidor
    salvar_dados_servidor()

@bot.event
async def on_guild_join(guild):
    from cargos import salvar_dados_servidor
    salvar_dados_servidor()

@bot.event
async def on_guild_remove(guild):
    from cargos import auto_roles, ticket_response_channels, mention_roles, sugestao_channels
    from cargos import salvar_dados_servidor
    guild_id = str(guild.id)
    auto_roles.pop(guild_id, None)
    ticket_response_channels.pop(guild_id, None)
    mention_roles.pop(guild_id, None)
    sugestao_channels.pop(guild_id, None)
    salvar_dados_servidor()

# ─── Setup dos comandos ────────────────────────────────────────────────────────

carregar_dados_servidor()
carregar_tipos_mensagem()
setup_aniversarios_commands(bot)
setup_mensagens_commands(bot)
setup_cargos_commands(bot)
setup_tickets_commands(bot)

# ─── Inicia o bot ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    bot.run(TOKEN)
