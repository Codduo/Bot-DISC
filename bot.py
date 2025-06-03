import discord
from discord.ext import commands, tasks
from discord import TextStyle
from discord.ui import View, Modal, TextInput, Button, Select
from discord import SelectOption
from math import ceil
import asyncio
import logging
import os
import json
import sys
import socket
import time
from datetime import datetime, date
from dotenv import load_dotenv

# ===== SINGLE INSTANCE CONTROL =====
def get_single_instance_lock():
    """Cria um socket para garantir que apenas uma instância rode."""
    try:
        # Criar um socket que será usado como lock
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Tentar fazer bind em uma porta específica
        # Se outra instância estiver rodando, isso falhará
        lock_socket.bind(('127.0.0.1', 65432))  # Porta específica para este bot
        lock_socket.listen(1)
        
        print("✅ Instância única confirmada - Bot pode iniciar")
        return lock_socket
        
    except OSError:
        print("❌ ERRO: Já existe uma instância do bot rodando!")
        print("🔍 Para verificar processos ativos:")
        print("   Linux/Mac: ps aux | grep python")
        print("   Windows: tasklist | findstr python")
        print("🛑 Encerrando para evitar duplicação...")
        sys.exit(1)

# ===== INITIALIZE LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

# Criar lock de instância única ANTES de tudo
lock_socket = get_single_instance_lock()

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== DATA STORAGE =====
auto_roles = {}
ticket_response_channels = {}
mention_roles = {}
sugestao_channels = {}
ticket_categories = {}
ticket_support_roles = {}
aniversario_channels = {}  # Novo: canais para enviar mensagens de aniversário

# Flag para controlar views
views_registered = False

# ===== ANIVERSÁRIO SYSTEM =====
def carregar_aniversarios():
    """Carrega os dados de aniversário do JSON."""
    # Tentar diferentes locais e nomes de arquivo possíveis
    locais_e_nomes = [
        # Na pasta atual
        "aniversarios.json",
        "aniversarios (1).json", 
        "aniversario.json",
        "Aniversarios.json",
        # Na subpasta Bot-DISC
        "Bot-DISC/aniversarios.json",
        "Bot-DISC/aniversarios (1).json",
        "Bot-DISC/aniversario.json",
        "Bot-DISC/Aniversarios.json",
        # Outros possíveis caminhos
        "./Bot-DISC/aniversarios.json",
        os.path.join("Bot-DISC", "aniversarios.json")
    ]
    
    for caminho_arquivo in locais_e_nomes:
        try:
            if os.path.exists(caminho_arquivo):
                with open(caminho_arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    print(f"✅ Arquivo {caminho_arquivo} carregado com {len(dados)} aniversários")
                    return dados
        except Exception as e:
            print(f"❌ Erro ao carregar {caminho_arquivo}: {e}")
            continue
    
    print("⚠️ Nenhum arquivo de aniversários encontrado")
    print("🔍 Locais procurados:", ", ".join(locais_e_nomes))
    return {}

def verificar_aniversariantes():
    """Verifica se há aniversariantes hoje."""
    aniversarios = carregar_aniversarios()
    hoje = date.today()
    aniversariantes = []
    
    print(f"🔍 Verificando aniversários para {hoje.strftime('%d/%m/%Y')} (dia {hoje.day}, mês {hoje.month})")
    
    for user_id, dados in aniversarios.items():
        try:
            # Converter string de data para objeto date
            data_nascimento = datetime.strptime(dados["data_nascimento"], "%Y-%m-%d").date()
            
            
            # Verificar se o dia e mês são iguais ao de hoje
            if data_nascimento.day == hoje.day and data_nascimento.month == hoje.month:
                # Calcular idade
                idade = hoje.year - data_nascimento.year
                aniversariante = {
                    "user_id": user_id,
                    "nome": dados["nome"],
                    "idade": idade,
                    "link_foto": dados["link_foto"]
                }
                aniversariantes.append(aniversariante)
                print(f"   ✅ ANIVERSARIANTE ENCONTRADO: {dados['nome']} ({idade} anos)")
                
        except Exception as e:
            print(f"   ⚠️ Erro ao processar aniversário de {user_id}: {e}")
    
    print(f"📊 Total de aniversariantes hoje: {len(aniversariantes)}")
    return aniversariantes

async def enviar_mensagem_aniversario(guild, aniversariante):
    """Envia mensagem de aniversário personalizada."""
    guild_id = str(guild.id)
    canal_id = aniversario_channels.get(guild_id)
    
    if not canal_id:
        return False
    
    canal = guild.get_channel(canal_id)
    if not canal:
        return False
    
    try:
        # Tentar pegar o membro do servidor
        member = guild.get_member(int(aniversariante["user_id"]))
        
        # Criar embed bonito
        embed = discord.Embed(
            title="🎉 FELIZ ANIVERSÁRIO! 🎂",
            description=f"**{aniversariante['nome']}** está fazendo **{aniversariante['idade']} anos** hoje! 🎈",
            color=0xFFD700  # Cor dourada
        )
        
        # Adicionar campos
        embed.add_field(
            name="🎁 Desejamos", 
            value="Muitas felicidades, saúde e prosperidade!", 
            inline=False
        )
        embed.add_field(
            name="🎊 Idade", 
            value=f"{aniversariante['idade']} anos", 
            inline=True
        )
        
        if member:
            embed.add_field(
                name="👤 Membro", 
                value=member.mention, 
                inline=True
            )
        
        # Adicionar foto se disponível
        if aniversariante["link_foto"] and aniversariante["link_foto"] != "https://drive.google.com/exemplo":
            embed.set_image(url=aniversariante["link_foto"])
        
        embed.set_footer(text=f"Data de nascimento: {aniversariante['nome']}")
        embed.timestamp = datetime.now()
        
        # Mensagem especial
        mensagens_especiais = [
            f"🎉 Todo mundo, vamos comemorar! Hoje é aniversário do(a) **{aniversariante['nome']}**! 🎂",
            f"🎈 Um feliz aniversário para nosso(a) querido(a) **{aniversariante['nome']}**! 🎁",
            f"🎊 Parabéns, **{aniversariante['nome']}**! Que este novo ano seja incrível! 🌟"
        ]
        
        import random
        mensagem = random.choice(mensagens_especiais)
        
        # Mencionar a pessoa se ela estiver no servidor
        if member:
            mensagem = f"{member.mention} {mensagem}"
        
        await canal.send(content=mensagem, embed=embed)
        return True
        
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem de aniversário: {e}")
        return False

@tasks.loop(hours=24)
async def verificar_aniversarios_task():
    """Task que roda todo dia para verificar aniversários."""
    print("🔍 Verificando aniversários do dia...")
    
    aniversariantes = verificar_aniversariantes()
    
    if not aniversariantes:
        print("ℹ️ Nenhum aniversariante hoje")
        return
    
    print(f"🎉 {len(aniversariantes)} aniversariante(s) encontrado(s)!")
    
    # Enviar mensagem para todos os servidores configurados
    for guild in bot.guilds:
        for aniversariante in aniversariantes:
            # Verificar se a pessoa está neste servidor
            member = guild.get_member(int(aniversariante["user_id"]))
            if member:  # Só enviar se a pessoa estiver no servidor
                sucesso = await enviar_mensagem_aniversario(guild, aniversariante)
                if sucesso:
                    print(f"✅ Mensagem de aniversário enviada para {aniversariante['nome']} em {guild.name}")
                else:
                    print(f"❌ Falha ao enviar mensagem para {aniversariante['nome']} em {guild.name}")

@verificar_aniversarios_task.before_loop
async def before_verificar_aniversarios():
    """Espera o bot estar pronto antes de começar a task."""
    await bot.wait_until_ready()
    print("🤖 Bot pronto - Iniciando verificação de aniversários")

# ===== CONFIGURAÇÕES DOS TIPOS DE SUPORTE =====
SUPPORT_TYPES = {
    "tecnico": {
        "name": "Suporte Técnico",
        "emoji": "🖥️",
        "role_id": 1359194954756264120,
        "description": "Para problemas técnicos e TI"
    },
    "kommo": {
        "name": "Suporte Kommo",
        "emoji": "📱",
        "role_id": 1373012855271719003,
        "description": "Para questões do sistema Kommo"
    },
    "rh": {
        "name": "Suporte RH",
        "emoji": "👥",
        "role_id": 1359505353653489694,
        "description": "Para questões de Recursos Humanos"
    },
    "gerencia": {
        "name": "Suporte Gerência",
        "emoji": "💼",
        "role_id": 1359504498048893070,
        "description": "Para questões gerenciais"
    }
}

# ===== DATA MANAGEMENT =====
def salvar_dados():
    dados = {
        "auto_roles": auto_roles,
        "ticket_response_channels": ticket_response_channels,
        "mention_roles": mention_roles,
        "sugestao_channels": sugestao_channels,
        "ticket_categories": ticket_categories,
        "ticket_support_roles": ticket_support_roles,
        "aniversario_channels": aniversario_channels,  # Novo campo
    }
    
    try:
        with open("dados_servidor.json", "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Erro ao salvar dados: {e}")

def carregar_dados():
    try:
        if os.path.exists("dados_servidor.json"):
            with open("dados_servidor.json", "r", encoding="utf-8") as f:
                dados = json.load(f)
                auto_roles.update(dados.get("auto_roles", {}))
                ticket_response_channels.update(dados.get("ticket_response_channels", {}))
                mention_roles.update(dados.get("mention_roles", {}))
                sugestao_channels.update(dados.get("sugestao_channels", {}))
                ticket_categories.update(dados.get("ticket_categories", {}))
                ticket_support_roles.update(dados.get("ticket_support_roles", {}))
                aniversario_channels.update(dados.get("aniversario_channels", {}))  # Novo campo
                print("✅ Dados carregados com sucesso")
    except Exception as e:
        print(f"⚠️ Erro ao carregar dados: {e}")

# ===== TICKET MODAL =====
class TicketModal(Modal, title="Solicitar Cargo"):
    nome = TextInput(label="Nome", placeholder="Digite seu nome completo", style=TextStyle.short)
    cargo = TextInput(label="Setor / Cargo desejado", placeholder="Ex: Financeiro, RH...", style=TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        mod_channel_id = ticket_response_channels.get(str(interaction.guild.id))
        mod_channel = bot.get_channel(mod_channel_id)
        cargo_id = mention_roles.get(str(interaction.guild.id))

        try:
            await interaction.user.edit(nick=self.nome.value)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não consegui alterar seu apelido", ephemeral=True)
            return

        if not mod_channel:
            await interaction.response.send_message("❌ Canal não configurado", ephemeral=True)
            return

        embed = discord.Embed(title="📉 Novo Pedido de Cargo", color=discord.Color.blurple())
        embed.add_field(name="Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="Cargo desejado", value=self.cargo.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        mention = f"<@&{cargo_id}>" if cargo_id else ""
        await mod_channel.send(content=mention, embed=embed)
        await interaction.response.send_message("✅ Pedido enviado!", ephemeral=True)

class TicketButton(Button):
    def __init__(self):
        super().__init__(label="Solicitar cargo", emoji="📬", style=discord.ButtonStyle.secondary, custom_id="ticket_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton())

# ===== TICKET SUPPORT SYSTEM =====
class TicketSupportModal(Modal, title="Abrir Ticket de Suporte"):
    assunto = TextInput(label="Assunto", placeholder="Descreva brevemente seu problema", style=TextStyle.short)
    descricao = TextInput(label="Descrição detalhada", placeholder="Explique seu problema em detalhes...", style=TextStyle.paragraph)

    def __init__(self, support_type):
        super().__init__()
        self.support_type = support_type
        self.title = f"Ticket - {SUPPORT_TYPES[support_type]['name']}"

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        category_id = ticket_categories.get(guild_id)
        
        if not category_id:
            await interaction.response.send_message("❌ Sistema não configurado", ephemeral=True)
            return
            
        category = interaction.guild.get_channel(category_id)
        
        if not category:
            await interaction.response.send_message("❌ Categoria não encontrada", ephemeral=True)
            return

        # Obter informações do tipo de suporte
        support_info = SUPPORT_TYPES[self.support_type]
        support_role = interaction.guild.get_role(support_info['role_id'])

        ticket_name = f"ticket-{self.support_type}-{interaction.user.name.lower().replace(' ', '-')}"
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        try:
            ticket_channel = await interaction.guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {interaction.user.display_name} - {support_info['name']}"
            )
            
            embed = discord.Embed(
                title=f"🎫 {support_info['name']}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Usuário", value=interaction.user.mention, inline=True)
            embed.add_field(name="📝 Assunto", value=self.assunto.value, inline=True)
            embed.add_field(name="🏷️ Tipo", value=f"{support_info['emoji']} {support_info['name']}", inline=True)
            embed.add_field(name="📄 Descrição", value=self.descricao.value, inline=False)
            embed.set_footer(text=f"ID do usuário: {interaction.user.id}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            close_view = TicketCloseView()
            
            mention_text = f"{interaction.user.mention}"
            if support_role:
                mention_text += f" <@&{support_info['role_id']}>"
                
            await ticket_channel.send(
                content=f"{mention_text}\n\n**Olá {interaction.user.mention}!** 👋\nSeu ticket de **{support_info['name']}** foi criado. Nossa equipe irá ajudar em breve.",
                embed=embed,
                view=close_view
            )
            
            await interaction.response.send_message(f"✅ Ticket criado: {ticket_channel.mention}", ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro: {str(e)}", ephemeral=True)

class SupportTypeSelect(Select):
    def __init__(self):
        options = []
        for key, info in SUPPORT_TYPES.items():
            options.append(SelectOption(
                label=info['name'],
                description=info['description'],
                emoji=info['emoji'],
                value=key
            ))
        
        super().__init__(
            placeholder="Selecione o tipo de suporte...",
            options=options,
            custom_id="support_type_select"
        )

    async def callback(self, interaction: discord.Interaction):
        support_type = self.values[0]
        modal = TicketSupportModal(support_type)
        await interaction.response.send_modal(modal)

class TicketSupportView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SupportTypeSelect())

# ===== CLOSE TICKET SYSTEM =====
class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        user_id = None
        
        try:
            async for message in interaction.channel.history(limit=20, oldest_first=True):
                if message.embeds and message.author == interaction.guild.me:
                    embed = message.embeds[0]
                    if embed.footer and "ID do usuário:" in embed.footer.text:
                        user_id = int(embed.footer.text.split("ID do usuário: ")[1])
                        break
        except:
            pass
        
        # Verificar se o usuário tem permissão (dono do ticket, admin, ou qualquer cargo de suporte)
        has_permission = (
            interaction.user.id == user_id or 
            interaction.user.guild_permissions.manage_channels or
            any(role.id in [info['role_id'] for info in SUPPORT_TYPES.values()] for role in interaction.user.roles)
        )
        
        if not has_permission:
            await interaction.response.send_message("❌ Sem permissão", ephemeral=True)
            return
            
        confirm_view = ConfirmCloseView()
        await interaction.response.send_message("⚠️ Fechar ticket?", view=confirm_view, ephemeral=True)

class ConfirmCloseView(View):
    def __init__(self):
        super().__init__(timeout=30)
        
    @discord.ui.button(label="✅ Sim", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.send_message("🔒 Fechando em 3s...")
            await asyncio.sleep(3)
            await interaction.channel.delete(reason="Ticket fechado")
        except:
            pass
            
    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("✅ Cancelado", ephemeral=True)

# ===== SUGGESTION SYSTEM =====
class SugestaoModal(Modal, title="Envie sua sugestão"):
    mensagem = TextInput(label="Escreva aqui", style=TextStyle.paragraph)

    async def on_submit(self, interaction):
        canal_id = sugestao_channels.get(str(interaction.guild.id))
        canal = bot.get_channel(canal_id)
        if canal:
            embed = discord.Embed(title="📢 Sugestão Anônima", description=self.mensagem.value, color=discord.Color.orange())
            embed.set_footer(text="Enviado anonimamente")
            await canal.send(embed=embed)
        await interaction.response.send_message("✅ Enviado!", ephemeral=True)

class SugestaoButton(Button):
    def __init__(self):
        super().__init__(label="Enviar sugestão", emoji="💡", style=discord.ButtonStyle.secondary, custom_id="sugestao_button")

    async def callback(self, interaction):
        await interaction.response.send_modal(SugestaoModal())

class SugestaoView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SugestaoButton())

# ===== BOT EVENTS =====
@bot.event
async def on_ready():
    global views_registered
    
    if not views_registered:
        print(f"✅ Bot conectado: {bot.user}")
        print(f"🔧 Registrando views persistentes...")
        
        try:
            bot.add_view(TicketButtonView())
            bot.add_view(SugestaoView())
            bot.add_view(TicketSupportView())
            bot.add_view(TicketCloseView())
            views_registered = True
            print("✅ Views registradas com sucesso")
            
            # Iniciar task de aniversários
            if not verificar_aniversarios_task.is_running():
                verificar_aniversarios_task.start()
                print("🎂 Sistema de aniversários iniciado")
                
        except Exception as e:
            print(f"❌ Erro ao registrar views: {e}")
    else:
        print("ℹ️ Bot reconectado - Views já registradas")

@bot.event
async def on_member_join(member):
    role_id = auto_roles.get(str(member.guild.id))
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
                print(f"✅ Cargo {role.name} dado para {member.name}")
            except Exception as e:
                print(f"❌ Erro ao dar cargo: {e}")

@bot.event
async def on_command_completion(ctx):
    salvar_dados()

@bot.event
async def on_guild_join(guild):
    salvar_dados()

@bot.event
async def on_guild_remove(guild):
    guild_id = str(guild.id)
    auto_roles.pop(guild_id, None)
    ticket_response_channels.pop(guild_id, None)
    mention_roles.pop(guild_id, None)
    sugestao_channels.pop(guild_id, None)
    ticket_categories.pop(guild_id, None)
    ticket_support_roles.pop(guild_id, None)
    aniversario_channels.pop(guild_id, None)  # Novo campo
    salvar_dados()

# ===== COMMANDS =====
@bot.command(aliases=["cargos"])
@commands.has_permissions(administrator=True)
async def cargo(ctx):
    roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
    options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]

    if not options:
        await ctx.send("⚠️ Nenhum cargo encontrado")
        return

    class RoleSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Selecione o cargo automático", options=options)

        async def callback(self, interaction: discord.Interaction):
            role_id = int(self.values[0])
            auto_roles[str(ctx.guild.id)] = role_id
            salvar_dados()
            role = ctx.guild.get_role(role_id)
            await interaction.response.send_message(f"✅ Cargo configurado: **{role.name}**", ephemeral=True)

    view = View()
    view.add_item(RoleSelect())
    await ctx.send("👥 Selecione o cargo automático:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def setcargo(ctx):
    roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
    options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]

    if not options:
        await ctx.send("⚠️ Nenhum cargo encontrado")
        return

    class MentionRoleSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Cargo para mencionar nos tickets", options=options)

        async def callback(self, interaction: discord.Interaction):
            role_id = int(self.values[0])
            mention_roles[str(ctx.guild.id)] = role_id
            salvar_dados()
            role = ctx.guild.get_role(role_id)
            await interaction.response.send_message(f"📌 Cargo mencionado: **{role.name}**", ephemeral=True)

    view = View()
    view.add_item(MentionRoleSelect())
    await ctx.send("🔣 Selecione o cargo para mencionar:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
    if not channels:
        await ctx.send("❌ Nenhum canal disponível")
        return

    options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in channels[:25]]

    class ChannelSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Canal para tickets", options=options)

        async def callback(self, interaction: discord.Interaction):
            channel_id = int(self.values[0])
            ticket_response_channels[str(ctx.guild.id)] = channel_id
            salvar_dados()
            await interaction.response.send_message(f"✅ Canal configurado: <#{channel_id}>", ephemeral=True)
            await ctx.send("📉 Solicite seu cargo:", view=TicketButtonView())

    view = View()
    view.add_item(ChannelSelect())
    await ctx.send("📌 Escolha o canal:", view=view)

# ===== COMANDO DE DEBUG =====
@bot.command()
@commands.has_permissions(administrator=True)
async def debugjson(ctx):
    """Debug para encontrar o arquivo JSON."""
    import os
    
    embed = discord.Embed(title="🔍 Debug - Arquivo JSON", color=discord.Color.yellow())
    
    # Verificar diretório atual
    diretorio_atual = os.getcwd()
    embed.add_field(name="📁 Diretório atual", value=f"`{diretorio_atual}`", inline=False)
    
    # Listar arquivos na pasta
    arquivos = os.listdir(diretorio_atual)
    arquivos_json = [f for f in arquivos if f.endswith('.json')]
    
    if arquivos_json:
        lista_json = "\n".join([f"`{arquivo}`" for arquivo in arquivos_json])
        embed.add_field(name="📄 Arquivos JSON encontrados", value=lista_json, inline=False)
    else:
        embed.add_field(name="📄 Arquivos JSON", value="❌ Nenhum arquivo .json encontrado", inline=False)
    
    # Verificar especificamente os nomes possíveis
    nomes_possiveis = ["aniversarios.json", "aniversarios (1).json", "aniversario.json"]
    for nome in nomes_possiveis:
        existe = os.path.exists(nome)
        status = "✅" if existe else "❌"
        embed.add_field(name=f"🔍 {nome}", value=f"{status} {'Existe' if existe else 'Não encontrado'}", inline=True)
    
    await ctx.send(embed=embed)

# ===== COMANDO DE ANIVERSÁRIO =====
@bot.command()
@commands.has_permissions(administrator=True)
async def aniversario(ctx):
    """Configura o canal para mensagens de aniversário."""
    channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
    if not channels:
        await ctx.send("❌ Nenhum canal disponível")
        return

    options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in channels[:25]]

    class AniversarioChannelSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Canal para mensagens de aniversário", options=options)

        async def callback(self, interaction: discord.Interaction):
            channel_id = int(self.values[0])
            aniversario_channels[str(ctx.guild.id)] = channel_id
            salvar_dados()
            await interaction.response.send_message(f"🎂 Canal de aniversários configurado: <#{channel_id}>", ephemeral=True)

    view = View()
    view.add_item(AniversarioChannelSelect())
    await ctx.send("🎉 Escolha o canal para aniversários:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def testaraniversario(ctx):
    """Testa o sistema de aniversário manualmente."""
    aniversariantes = verificar_aniversariantes()
    
    if not aniversariantes:
        await ctx.send("ℹ️ Nenhum aniversariante encontrado para hoje")
        return
    
    # Verificar se o canal está configurado
    guild_id = str(ctx.guild.id)
    if guild_id not in aniversario_channels:
        await ctx.send("❌ Configure o canal de aniversários primeiro com `!aniversario`")
        return
    
    enviados = 0
    for aniversariante in aniversariantes:
        # Verificar se a pessoa está neste servidor
        member = ctx.guild.get_member(int(aniversariante["user_id"]))
        if member:
            sucesso = await enviar_mensagem_aniversario(ctx.guild, aniversariante)
            if sucesso:
                enviados += 1
    
    await ctx.send(f"✅ {enviados} mensagem(s) de aniversário enviada(s)!")

@bot.command()
@commands.has_permissions(administrator=True)
async def debuganiversarios(ctx):
    """Debug detalhado dos aniversários."""
    aniversarios = carregar_aniversarios()
    
    if not aniversarios:
        await ctx.send("❌ Nenhum aniversário carregado")
        return
    
    hoje = date.today()
    embed = discord.Embed(title="🔍 Debug Aniversários Detalhado", color=discord.Color.blue())
    
    # Informações básicas
    embed.add_field(name="📅 Data de hoje", value=f"{hoje.strftime('%d/%m/%Y')} (dia {hoje.day}, mês {hoje.month})", inline=False)
    embed.add_field(name="📊 Total carregado", value=f"{len(aniversarios)} pessoas", inline=True)
    
    # Verificar aniversários de junho
    junho_count = 0
    aniversariantes_junho = []
    hoje_count = 0
    
    for user_id, dados in aniversarios.items():
        try:
            # Debug da data
            data_str = dados["data_nascimento"]
            data_nascimento = datetime.strptime(data_str, "%Y-%m-%d").date()
            
            # Verificar se é junho
            if data_nascimento.month == 6:
                junho_count += 1
                member = ctx.guild.get_member(int(user_id))
                status = "✅" if member else "❌"
                aniversariantes_junho.append(f"**{data_nascimento.day}/06** - {dados['nome'][:15]}... {status}")
                
                # Verificar se é hoje
                if data_nascimento.day == hoje.day and data_nascimento.month == hoje.month:
                    hoje_count += 1
                    
        except Exception as e:
            embed.add_field(name=f"❌ Erro em {user_id}", value=f"Data: {dados.get('data_nascimento', 'N/A')}\nErro: {str(e)[:50]}", inline=True)
    
    embed.add_field(name="🎂 Aniversários em Junho", value=f"{junho_count} pessoas", inline=True)
    embed.add_field(name="🎉 Aniversários HOJE", value=f"{hoje_count} pessoas", inline=True)
    
    # Mostrar alguns aniversários de junho
    if aniversariantes_junho:
        lista_junho = "\n".join(aniversariantes_junho[:10])  # Máximo 10
        if len(aniversariantes_junho) > 10:
            lista_junho += f"\n... e mais {len(aniversariantes_junho) - 10}"
        embed.add_field(name="📋 Aniversários de Junho", value=lista_junho, inline=False)
    
    # Mostrar 3 exemplos de datas do JSON para debug
    exemplos = []
    for i, (user_id, dados) in enumerate(list(aniversarios.items())[:3]):
        try:
            data_str = dados["data_nascimento"]
            data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
            exemplos.append(f"`{data_str}` → Dia {data_obj.day}, Mês {data_obj.month}")
        except:
            exemplos.append(f"`{dados.get('data_nascimento', 'N/A')}` → ERRO")
    
    embed.add_field(name="🔍 Exemplos de datas", value="\n".join(exemplos), inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def carregarjson(ctx):
    """Força o carregamento do JSON manualmente."""
    try:
        aniversarios = carregar_aniversarios()
        
        if aniversarios:
            embed = discord.Embed(title="✅ JSON Carregado!", color=discord.Color.green())
            embed.add_field(name="📊 Total de pessoas", value=len(aniversarios), inline=True)
            
            # Mostrar algumas amostras
            amostras = list(aniversarios.items())[:3]
            for user_id, dados in amostras:
                member = ctx.guild.get_member(int(user_id))
                status = "✅ No servidor" if member else "❌ Não está no servidor"
                embed.add_field(
                    name=f"👤 {dados['nome'][:20]}...", 
                    value=f"Nascimento: {dados['data_nascimento']}\n{status}", 
                    inline=True
                )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Não foi possível carregar o arquivo JSON")
            
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@bot.command()
async def listaraniversarios(ctx):
    """Lista todos os aniversários do mês atual."""
    aniversarios = carregar_aniversarios()
    hoje = date.today()
    mes_atual = hoje.month
    
    print(f"🔍 Listando aniversários do mês {mes_atual} ({hoje.strftime('%B')})")
    
    aniversariantes_mes = []
    
    for user_id, dados in aniversarios.items():
        try:
            data_nascimento = datetime.strptime(dados["data_nascimento"], "%Y-%m-%d").date()
            print(f"   Verificando {dados['nome']}: nascimento mês {data_nascimento.month}")
            
            if data_nascimento.month == mes_atual:
                # Verificar se a pessoa está no servidor
                member = ctx.guild.get_member(int(user_id))
                if member:  # Só adicionar se estiver no servidor
                    aniversariantes_mes.append({
                        "dia": data_nascimento.day,
                        "nome": dados["nome"],
                        "member": member
                    })
                    print(f"   ✅ Adicionado: {dados['nome']} (dia {data_nascimento.day})")
                else:
                    print(f"   ❌ {dados['nome']} não está no servidor")
        except Exception as e:
            print(f"   ⚠️ Erro com {user_id}: {e}")
            continue
    
    print(f"📊 Total encontrado no servidor: {len(aniversariantes_mes)}")
    
    if not aniversariantes_mes:
        embed = discord.Embed(
            title=f"ℹ️ Aniversários de {datetime.now().strftime('%B')}",
            description="Nenhum aniversariante neste mês no servidor",
            color=discord.Color.orange()
        )
        embed.add_field(name="🔍 Debug", value=f"Verificados: {len(aniversarios)} registros\nMês atual: {mes_atual}", inline=False)
        await ctx.send(embed=embed)
        return
    
    # Ordenar por dia
    aniversariantes_mes.sort(key=lambda x: x["dia"])
    
    embed = discord.Embed(
        title=f"🎂 Aniversariantes de {datetime.now().strftime('%B')}",
        color=discord.Color.gold()
    )
    
    lista = ""
    for aniv in aniversariantes_mes:
        status = "🎉 **HOJE!**" if aniv["dia"] == hoje.day else ""
        lista += f"**{aniv['dia']:02d}** - {aniv['nome']} {status}\n"
    
    embed.description = lista
    embed.set_footer(text=f"Total: {len(aniversariantes_mes)} aniversariante(s) no servidor")
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setupticket(ctx):
    """Configura o sistema de tickets em duas etapas."""
    guild_id = str(ctx.guild.id)
    categories = ctx.guild.categories
    
    if not categories:
        await ctx.send("❌ **Erro:** Não há categorias no servidor.\n📁 Crie uma categoria primeiro usando as configurações do servidor.")
        return
        
    # Criar lista de categorias
    category_list = "\n".join([f"`{i+1}.` {cat.name}" for i, cat in enumerate(categories[:10])])
    
    embed = discord.Embed(
        title="📁 Configuração de Tickets - Categoria",
        description=f"**Categorias disponíveis:**\n{category_list}\n\n**Digite o número da categoria desejada:**",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed)
    
    def check_category(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()
    
    try:
        # Aguardar resposta do usuário para categoria
        msg = await bot.wait_for('message', check=check_category, timeout=30.0)
        category_num = int(msg.content) - 1
        
        if 0 <= category_num < len(categories):
            selected_category = categories[category_num]
            ticket_categories[guild_id] = selected_category.id
            salvar_dados()
            
            # Confirmação final
            success_embed = discord.Embed(
                title="✅ Sistema de Tickets Configurado!",
                color=discord.Color.green()
            )
            success_embed.add_field(name="📁 Categoria", value=selected_category.name, inline=True)
            success_embed.add_field(name="🎯 Tipos Disponíveis", value="\n".join([f"{info['emoji']} {info['name']}" for info in SUPPORT_TYPES.values()]), inline=False)
            success_embed.add_field(name="📋 Próximo Passo", value="Use `!ticketpanel` para criar o painel", inline=False)
            
            await ctx.send(embed=success_embed)
            
        else:
            await ctx.send("❌ **Erro:** Número de categoria inválido. Use `!setupticket` novamente.")
            
    except asyncio.TimeoutError:
        await ctx.send("⏰ **Tempo esgotado!** Use `!setupticket` novamente.")
    except ValueError:
        await ctx.send("❌ **Erro:** Digite apenas números. Use `!setupticket` novamente.")

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    guild_id = str(ctx.guild.id)
    
    if guild_id not in ticket_categories:
        await ctx.send("❌ Use `!setupticket` primeiro")
        return
        
    embed = discord.Embed(
        title="🎫 Sistema de Suporte",
        description="**Precisa de ajuda?** Selecione o tipo de suporte!\n\n"
                   "**📋 Tipos disponíveis:**\n"
                   f"{SUPPORT_TYPES['tecnico']['emoji']} **{SUPPORT_TYPES['tecnico']['name']}** - {SUPPORT_TYPES['tecnico']['description']}\n"
                   f"{SUPPORT_TYPES['kommo']['emoji']} **{SUPPORT_TYPES['kommo']['name']}** - {SUPPORT_TYPES['kommo']['description']}\n"
                   f"{SUPPORT_TYPES['rh']['emoji']} **{SUPPORT_TYPES['rh']['name']}** - {SUPPORT_TYPES['rh']['description']}\n"
                   f"{SUPPORT_TYPES['gerencia']['emoji']} **{SUPPORT_TYPES['gerencia']['name']}** - {SUPPORT_TYPES['gerencia']['description']}\n\n"
                   "✅ **Como funciona:**\n"
                   "• Selecione o tipo de suporte\n"
                   "• Preencha o formulário\n"
                   "• Canal privado será criado\n"
                   "• Equipe especializada te ajudará\n\n"
                   "⚠️ **Use apenas para suporte real**",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Selecione o tipo de suporte no menu abaixo")
    
    await ctx.send(embed=embed, view=TicketSupportView())

@bot.command()
@commands.has_permissions(administrator=True)
async def reclamacao(ctx):
    canais = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
    options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in canais[:25]]

    class CanalSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Canal para sugestões", options=options)

        async def callback(self, interaction):
            canal_id = int(self.values[0])
            sugestao_channels[str(ctx.guild.id)] = canal_id
            salvar_dados()
            await interaction.response.send_message("✅ Canal configurado!", ephemeral=True)
            await ctx.send("**📜 Envie sugestões anonimamente:**", view=SugestaoView())

    view = View()
    view.add_item(CanalSelect())
    await ctx.send("🔹 Escolha o canal:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx):
    class ConfirmarLimpeza(Button):
        def __init__(self):
            super().__init__(label="Sim, limpar!", style=discord.ButtonStyle.danger)

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Apenas o autor pode confirmar", ephemeral=True)
                return

            await interaction.response.send_message("🧹 Limpando...")
            await asyncio.sleep(2)
            await ctx.channel.purge()
            
            aviso = await ctx.send("✅ Canal limpo!")
            await asyncio.sleep(3)
            await aviso.delete()

    view = View()
    view.add_item(ConfirmarLimpeza())
    await ctx.send("⚠️ Limpar todas as mensagens?", view=view)

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latência: `{round(bot.latency * 1000)}ms`")

@bot.command()
async def status(ctx):
    embed = discord.Embed(title="🤖 Status do Bot", color=discord.Color.green())
    embed.add_field(name="📊 Status", value="✅ Online", inline=True)
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Usuários", value=len(bot.users), inline=True)
    embed.add_field(name="📋 Views", value="✅ Ativas" if views_registered else "❌ Inativas", inline=True)
    embed.add_field(name="🔒 Instância", value="✅ Única", inline=True)
    embed.add_field(name="🎂 Aniversários", value="✅ Ativo" if verificar_aniversarios_task.is_running() else "❌ Inativo", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="ajuda")
async def ajuda(ctx):
    embed = discord.Embed(title="📖 Comandos", color=discord.Color.green())
    embed.add_field(name="!cargo", value="Cargo automático", inline=False)
    embed.add_field(name="!ticket", value="Sistema de pedidos", inline=False)
    embed.add_field(name="!setcargo", value="Cargo para mencionar", inline=False)
    embed.add_field(name="!setupticket", value="Configurar tickets", inline=False)
    embed.add_field(name="!ticketpanel", value="Painel de tickets", inline=False)
    embed.add_field(name="!reclamacao", value="Sugestões anônimas", inline=False)
    embed.add_field(name="!aniversario", value="🎂 Configurar aniversários", inline=False)
    embed.add_field(name="!listaraniversarios", value="🎉 Ver aniversários do mês", inline=False)
    embed.add_field(name="!testaraniversario", value="🧪 Testar sistema (Admin)", inline=False)
    embed.add_field(name="!debuganiversarios", value="🔍 Debug detalhado (Admin)", inline=False)
    embed.add_field(name="!carregarjson", value="📁 Carregar JSON (Admin)", inline=False)
    embed.add_field(name="!clear", value="Limpar canal", inline=False)
    embed.add_field(name="!ping", value="Testar bot", inline=False)
    embed.add_field(name="!status", value="Status do bot", inline=False)
    
    await ctx.send(embed=embed)

# ===== ERROR HANDLING =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Sem permissão para este comando")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Erro: {error}")

# ===== CLEANUP ON EXIT =====
def cleanup_on_exit():
    """Limpa recursos ao sair."""
    try:
        if 'lock_socket' in globals():
            lock_socket.close()
        print("🧹 Recursos limpos")
    except:
        pass

import atexit
atexit.register(cleanup_on_exit)

# ===== MAIN =====
if __name__ == "__main__":
    try:
        print("🚀 Iniciando Bot Bmz Server...")
        print(f"🔒 PID: {os.getpid()}")
        
        # Carregar dados
        carregar_dados()
        
        # Carregar token
        load_dotenv()
        TOKEN = os.getenv("DISCORD_TOKEN")
        
        if not TOKEN:
            print("❌ Token não encontrado no .env")
            sys.exit(1)
        
        # Iniciar bot
        bot.run(TOKEN)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
    finally:
        cleanup_on_exit()
        sys.exit(0)
