@bot.command(name="ajuda")
async def ajuda(ctx):
    embed = discord.Embed(title="📖 Comandos", color=discord.Color.green())
    embed.add_field(name="**🎭 Sistema de Cargos**", value="", inline=False)
    embed.add_field(name="!cargo", value="Configurar cargo automático", inline=True)
    embed.add_field(name="!setcargo", value="Cargo para mencionar", inline=True)
    
    embed.add_field(name="**🎫 Sistema de Tickets**", value="", inline=Falseimport discord
from discord.ext import commands
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
from datetime import datetime
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
log_channels = {}  # Canal de logs por servidor

# Flag para controlar views
views_registered = False

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
        "log_channels": log_channels,
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
                log_channels.update(dados.get("log_channels", {}))
                print("✅ Dados carregados com sucesso")
    except Exception as e:
        print(f"⚠️ Erro ao carregar dados: {e}")

# ===== SISTEMA DE LOGS =====
async def enviar_log(guild, titulo, descricao, cor=discord.Color.blue(), campos=None, thumbnail=None):
    """Envia log para o canal configurado ou servidor de logs"""
    try:
        guild_id = str(guild.id)
        log_channel_id = log_channels.get(guild_id)
        
        if not log_channel_id:
            return  # Sem canal configurado
            
        log_channel = bot.get_channel(log_channel_id)
        if not log_channel:
            return  # Canal não encontrado
            
        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=cor,
            timestamp=datetime.now()
        )
        
        if campos:
            for campo in campos:
                embed.add_field(
                    name=campo.get("name", "Campo"),
                    value=campo.get("value", "Valor"),
                    inline=campo.get("inline", True)
                )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
            
        embed.set_footer(text=f"Servidor: {guild.name}", icon_url=guild.icon.url if guild.icon else None)
        
        await log_channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Erro ao enviar log: {e}")

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
            
            # Log da criação do ticket
            await enviar_log(
                interaction.guild,
                "🎫 Ticket Criado",
                f"Novo ticket de suporte foi aberto",
                discord.Color.green(),
                [
                    {"name": "👤 Usuário", "value": f"{interaction.user.mention} ({interaction.user.id})", "inline": True},
                    {"name": "🏷️ Tipo", "value": f"{support_info['emoji']} {support_info['name']}", "inline": True},
                    {"name": "📝 Assunto", "value": self.assunto.value[:100] + ("..." if len(self.assunto.value) > 100 else ""), "inline": False},
                    {"name": "📍 Canal", "value": ticket_channel.mention, "inline": True}
                ],
                interaction.user.display_avatar.url
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
            # Coletar informações do ticket antes de fechar
            ticket_info = {"user": "Desconhecido", "type": "Desconhecido"}
            
            async for message in interaction.channel.history(limit=20, oldest_first=True):
                if message.embeds and message.author == interaction.guild.me:
                    embed = message.embeds[0]
                    if "👤 Usuário" in embed.description or any("👤 Usuário" in field.name for field in embed.fields):
                        for field in embed.fields:
                            if field.name == "👤 Usuário":
                                user_mention = field.value.split()[0]
                                ticket_info["user"] = user_mention
                            elif field.name == "🏷️ Tipo":
                                ticket_info["type"] = field.value
                        break
            
            channel_name = interaction.channel.name
            
            await interaction.response.send_message("🔒 Fechando em 3s...")
            
            # Log do fechamento do ticket
            await enviar_log(
                interaction.guild,
                "🔒 Ticket Fechado",
                f"Ticket foi fechado",
                discord.Color.red(),
                [
                    {"name": "👤 Usuario do Ticket", "value": ticket_info["user"], "inline": True},
                    {"name": "🏷️ Tipo", "value": ticket_info["type"], "inline": True},
                    {"name": "🔒 Fechado por", "value": f"{interaction.user.mention} ({interaction.user.id})", "inline": True},
                    {"name": "📍 Canal", "value": f"#{channel_name}", "inline": True}
                ],
                interaction.user.display_avatar.url
            )
            
            await asyncio.sleep(3)
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user.name}")
        except Exception as e:
            print(f"Erro ao fechar ticket: {e}")
            
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
                
                # Log de entrada do membro
                await enviar_log(
                    member.guild,
                    "👋 Membro Entrou",
                    f"Novo membro entrou no servidor",
                    discord.Color.green(),
                    [
                        {"name": "👤 Usuário", "value": f"{member.mention} ({member.id})", "inline": True},
                        {"name": "📅 Conta Criada", "value": f"<t:{int(member.created_at.timestamp())}:R>", "inline": True},
                        {"name": "🎭 Cargo Automático", "value": role.mention if role else "Nenhum", "inline": True}
                    ],
                    member.display_avatar.url
                )
            except Exception as e:
                print(f"❌ Erro ao dar cargo: {e}")

@bot.event
async def on_member_remove(member):
    # Log de saída do membro
    await enviar_log(
        member.guild,
        "👋 Membro Saiu",
        f"Membro saiu do servidor",
        discord.Color.orange(),
        [
            {"name": "👤 Usuário", "value": f"{member.name}#{member.discriminator} ({member.id})", "inline": True},
            {"name": "📅 Entrou em", "value": f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Desconhecido", "inline": True},
            {"name": "🎭 Cargos", "value": ", ".join([role.name for role in member.roles[1:]][:5]) or "Nenhum", "inline": False}
        ],
        member.display_avatar.url
    )

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
        
    # Log de mensagem deletada
    await enviar_log(
        message.guild,
        "🗑️ Mensagem Deletada",
        f"Mensagem foi deletada",
        discord.Color.red(),
        [
            {"name": "👤 Autor", "value": f"{message.author.mention} ({message.author.id})", "inline": True},
            {"name": "📍 Canal", "value": f"{message.channel.mention}", "inline": True},
            {"name": "📝 Conteúdo", "value": message.content[:500] + ("..." if len(message.content) > 500 else "") if message.content else "*Sem conteúdo de texto*", "inline": False},
            {"name": "📅 Enviada em", "value": f"<t:{int(message.created_at.timestamp())}:R>", "inline": True}
        ],
        message.author.display_avatar.url
    )

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
        
    # Log de mensagem editada
    await enviar_log(
        before.guild,
        "✏️ Mensagem Editada",
        f"Mensagem foi editada",
        discord.Color.yellow(),
        [
            {"name": "👤 Autor", "value": f"{before.author.mention} ({before.author.id})", "inline": True},
            {"name": "📍 Canal", "value": f"{before.channel.mention}", "inline": True},
            {"name": "📝 Antes", "value": before.content[:300] + ("..." if len(before.content) > 300 else "") if before.content else "*Sem conteúdo*", "inline": False},
            {"name": "📝 Depois", "value": after.content[:300] + ("..." if len(after.content) > 300 else "") if after.content else "*Sem conteúdo*", "inline": False}
        ],
        before.author.display_avatar.url
    )

@bot.event
async def on_voice_state_update(member, before, after):
    # Log de movimentação de voz
    if before.channel != after.channel:
        if before.channel is None:  # Entrou em call
            await enviar_log(
                member.guild,
                "🔊 Entrou em Call",
                f"Membro entrou em canal de voz",
                discord.Color.green(),
                [
                    {"name": "👤 Usuário", "value": f"{member.mention} ({member.id})", "inline": True},
                    {"name": "📍 Canal", "value": f"🔊 {after.channel.name}", "inline": True},
                    {"name": "👥 Pessoas no Canal", "value": str(len(after.channel.members)), "inline": True}
                ],
                member.display_avatar.url
            )
        elif after.channel is None:  # Saiu da call
            await enviar_log(
                member.guild,
                "🔇 Saiu de Call",
                f"Membro saiu de canal de voz",
                discord.Color.red(),
                [
                    {"name": "👤 Usuário", "value": f"{member.mention} ({member.id})", "inline": True},
                    {"name": "📍 Canal", "value": f"🔊 {before.channel.name}", "inline": True},
                    {"name": "👥 Pessoas Restantes", "value": str(len(before.channel.members)), "inline": True}
                ],
                member.display_avatar.url
            )
        else:  # Mudou de canal
            await enviar_log(
                member.guild,
                "🔄 Mudou de Call",
                f"Membro mudou de canal de voz",
                discord.Color.blue(),
                [
                    {"name": "👤 Usuário", "value": f"{member.mention} ({member.id})", "inline": True},
                    {"name": "📍 De", "value": f"🔊 {before.channel.name}", "inline": True},
                    {"name": "📍 Para", "value": f"🔊 {after.channel.name}", "inline": True}
                ],
                member.display_avatar.url
            )

@bot.event
async def on_guild_channel_delete(channel):
    # Log de canal deletado
    await enviar_log(
        channel.guild,
        "🗑️ Canal Deletado",
        f"Canal foi deletado",
        discord.Color.red(),
        [
            {"name": "📍 Nome", "value": f"#{channel.name}", "inline": True},
            {"name": "🏷️ Tipo", "value": str(channel.type).title(), "inline": True},
            {"name": "📁 Categoria", "value": channel.category.name if channel.category else "Nenhuma", "inline": True}
        ]
    )

@bot.event
async def on_guild_channel_create(channel):
    # Log de canal criado
    await enviar_log(
        channel.guild,
        "➕ Canal Criado",
        f"Novo canal foi criado",
        discord.Color.green(),
        [
            {"name": "📍 Nome", "value": f"{channel.mention}", "inline": True},
            {"name": "🏷️ Tipo", "value": str(channel.type).title(), "inline": True},
            {"name": "📁 Categoria", "value": channel.category.name if channel.category else "Nenhuma", "inline": True}
        ]
    )

@bot.event
async def on_member_update(before, after):
    # Log de mudanças no membro (nick, cargos)
    if before.nick != after.nick:
        await enviar_log(
            after.guild,
            "✏️ Apelido Alterado",
            f"Apelido de membro foi alterado",
            discord.Color.blue(),
            [
                {"name": "👤 Usuário", "value": f"{after.mention} ({after.id})", "inline": True},
                {"name": "📝 Antes", "value": before.nick or before.name, "inline": True},
                {"name": "📝 Depois", "value": after.nick or after.name, "inline": True}
            ],
            after.display_avatar.url
        )
    
    # Verificar mudanças de cargos
    if before.roles != after.roles:
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        
        if added_roles:
            await enviar_log(
                after.guild,
                "➕ Cargo Adicionado",
                f"Cargo foi adicionado ao membro",
                discord.Color.green(),
                [
                    {"name": "👤 Usuário", "value": f"{after.mention} ({after.id})", "inline": True},
                    {"name": "🎭 Cargos Adicionados", "value": ", ".join([role.mention for role in added_roles]), "inline": False}
                ],
                after.display_avatar.url
            )
        
        if removed_roles:
            await enviar_log(
                after.guild,
                "➖ Cargo Removido",
                f"Cargo foi removido do membro",
                discord.Color.red(),
                [
                    {"name": "👤 Usuário", "value": f"{after.mention} ({after.id})", "inline": True},
                    {"name": "🎭 Cargos Removidos", "value": ", ".join([role.name for role in removed_roles]), "inline": False}
                ],
                after.display_avatar.url
            )

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
    log_channels.pop(guild_id, None)
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
async def setlogs(ctx):
    """Configura o canal ou servidor de logs"""
    
    embed1 = discord.Embed(
        title="📊 Configuração de Logs",
        description="**Escolha uma opção:**\n\n"
                   "🏠 **Mesmo Servidor** - Canal no servidor atual\n"
                   "🌐 **Outro Servidor** - Canal em servidor diferente\n\n"
                   "**Digite:**\n"
                   "`1` - Para canal no mesmo servidor\n"
                   "`2` - Para canal em outro servidor",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed1)
    
    def check_option(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and msg.content in ['1', '2']
    
    try:
        msg = await bot.wait_for('message', check=check_option, timeout=30.0)
        option = msg.content
        
        if option == '1':
            # Canal no mesmo servidor
            channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
            if not channels:
                await ctx.send("❌ Nenhum canal disponível")
                return
                
            channel_list = "\n".join([f"`{i+1}.` {c.mention}" for i, c in enumerate(channels[:15])])
            
            embed2 = discord.Embed(
                title="📍 Selecionar Canal de Logs",
                description=f"**Canais disponíveis:**\n{channel_list}\n\n**Digite o número do canal:**",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed2)
            
            def check_channel(msg):
                return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()
            
            try:
                msg2 = await bot.wait_for('message', check=check_channel, timeout=30.0)
                channel_num = int(msg2.content) - 1
                
                if 0 <= channel_num < len(channels):
                    selected_channel = channels[channel_num]
                    log_channels[str(ctx.guild.id)] = selected_channel.id
                    salvar_dados()
                    
                    await ctx.send(f"✅ **Canal de logs configurado:** {selected_channel.mention}")
                else:
                    await ctx.send("❌ Número inválido")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Tempo esgotado")
                
        elif option == '2':
            # Canal em outro servidor
            embed2 = discord.Embed(
                title="🌐 Canal em Outro Servidor",
                description="**Para configurar logs em outro servidor:**\n\n"
                           "1️⃣ Copie o **ID do canal** de destino\n"
                           "2️⃣ Certifique-se que o bot está no servidor\n"
                           "3️⃣ Digite o ID do canal aqui\n\n"
                           "**💡 Como pegar ID do canal:**\n"
                           "• Ative o Modo Desenvolvedor no Discord\n"
                           "• Clique com botão direito no canal\n"
                           "• Selecione 'Copiar ID'",
                color=discord.Color.orange()
            )
            
            await ctx.send(embed=embed2)
            
            def check_channel_id(msg):
                return msg.author == ctx.author and msg.channel == ctx.channel and msg.content.isdigit()
            
            try:
                msg2 = await bot.wait_for('message', check=check_channel_id, timeout=60.0)
                channel_id = int(msg2.content)
                
                # Verificar se o canal existe e se o bot tem acesso
                target_channel = bot.get_channel(channel_id)
                
                if target_channel:
                    try:
                        # Testar se consegue enviar mensagem
                        test_embed = discord.Embed(
                            title="🧪 Teste de Logs",
                            description=f"Logs do servidor **{ctx.guild.name}** configurados com sucesso!",
                            color=discord.Color.green()
                        )
                        await target_channel.send(embed=test_embed)
                        
                        log_channels[str(ctx.guild.id)] = channel_id
                        salvar_dados()
                        
                        await ctx.send(f"✅ **Canal de logs configurado:** `{target_channel.name}` em `{target_channel.guild.name}`")
                        
                    except discord.Forbidden:
                        await ctx.send("❌ Sem permissão para enviar no canal especificado")
                    except Exception as e:
                        await ctx.send(f"❌ Erro ao testar o canal: {str(e)}")
                else:
                    await ctx.send("❌ Canal não encontrado. Verifique se o ID está correto e se o bot está no servidor.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Tempo esgotado")
            except ValueError:
                await ctx.send("❌ ID inválido")
                
    except asyncio.TimeoutError:
        await ctx.send("⏰ Tempo esgotado")

@bot.command()
@commands.has_permissions(administrator=True)
async def testlog(ctx):
    """Testa o sistema de logs"""
    await enviar_log(
        ctx.guild,
        "🧪 Teste de Sistema",
        "Este é um teste do sistema de logs",
        discord.Color.purple(),
        [
            {"name": "👤 Testado por", "value": f"{ctx.author.mention}", "inline": True},
            {"name": "📍 Canal", "value": f"{ctx.channel.mention}", "inline": True},
            {"name": "⏰ Status", "value": "✅ Sistema Funcionando", "inline": True}
        ],
        ctx.author.display_avatar.url
    )
    
    await ctx.send("🧪 **Teste enviado!** Verifique o canal de logs.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removelogs(ctx):
    """Remove a configuração de logs"""
    guild_id = str(ctx.guild.id)
    
    if guild_id in log_channels:
        log_channels.pop(guild_id)
        salvar_dados()
        await ctx.send("✅ **Sistema de logs desativado**")
    else:
        await ctx.send("❌ **Sistema de logs não estava configurado**")
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
    
    await ctx.send(embed=embed)

@bot.command(name="ajuda")
async def ajuda(ctx):
    embed = discord.Embed(title="📖 Comandos do Bot", color=discord.Color.green())
    
    embed.add_field(name="**🎭 Sistema de Cargos**", value="", inline=False)
    embed.add_field(name="!cargo", value="Configurar cargo automático", inline=True)
    embed.add_field(name="!setcargo", value="Cargo para mencionar", inline=True)
    
    embed.add_field(name="**🎫 Sistema de Tickets**", value="", inline=False)
    embed.add_field(name="!ticket", value="Sistema de pedidos de cargo", inline=True)
    embed.add_field(name="!setupticket", value="Configurar sistema de suporte", inline=True)
    embed.add_field(name="!ticketpanel", value="Criar painel de tickets", inline=True)
    
    embed.add_field(name="**💡 Sistema de Sugestões**", value="", inline=False)
    embed.add_field(name="!reclamacao", value="Configurar sugestões anônimas", inline=True)
    
    embed.add_field(name="**📊 Sistema de Logs**", value="", inline=False)
    embed.add_field(name="!setlogs", value="Configurar canal de logs", inline=True)
    embed.add_field(name="!testlog", value="Testar sistema de logs", inline=True)
    embed.add_field(name="!removelogs", value="Desativar logs", inline=True)
    
    embed.add_field(name="**🛠️ Utilitários**", value="", inline=False)
    embed.add_field(name="!clear", value="Limpar canal", inline=True)
    embed.add_field(name="!ping", value="Verificar latência", inline=True)
    embed.add_field(name="!status", value="Status do bot", inline=True)
    
    embed.set_footer(text="Use !comando para executar • Apenas administradores podem usar a maioria dos comandos")
    
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
