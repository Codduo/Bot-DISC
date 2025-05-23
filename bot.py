import discord
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
import signal
from datetime import datetime
from dotenv import load_dotenv

# ===== CONFIG =====
LOCKFILE = "/tmp/bot_bmz.lock"

# ===== INITIALIZE LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

# ===== BOT SETUP =====
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== DATA STORAGE =====
auto_roles = {}  # guild_id: role_id
ticket_response_channels = {}  # guild_id: channel_id
mention_roles = {}  # guild_id: cargo que será mencionado nos tickets
sugestao_channels = {}  # guild_id: canal para sugestões/reclamações
ticket_categories = {}  # guild_id: category_id onde os tickets serão criados
ticket_support_roles = {}  # guild_id: role_id do cargo de suporte

# Variável para controlar se as views já foram adicionadas
views_added = False

# ===== IMPROVED LOCK FILE MANAGEMENT =====
def check_lock_file():
    """Verifica e cria lock file com melhor detecção de processos."""
    if os.path.exists(LOCKFILE):
        try:
            with open(LOCKFILE, "r") as f:
                content = f.read().strip()
                if not content:
                    # Arquivo vazio, remover
                    os.remove(LOCKFILE)
                else:
                    old_pid = int(content)
            
            # Verificar se o processo ainda existe (método mais robusto)
            try:
                # No Linux/Mac, verificar se o processo existe
                if os.name != 'nt':  # Unix-like systems
                    os.kill(old_pid, 0)
                else:  # Windows
                    import psutil
                    if psutil.pid_exists(old_pid):
                        process = psutil.Process(old_pid)
                        # Verificar se é realmente nosso bot
                        if 'python' in process.name().lower():
                            print("⚠️ Já existe uma instância do bot rodando.")
                            print(f"PID da instância existente: {old_pid}")
                            print("❌ Para forçar a execução, delete o arquivo:", LOCKFILE)
                            sys.exit(1)
                    
                print("🧹 Removendo arquivo de lock órfão...")
                os.remove(LOCKFILE)
                        
            except (OSError, ProcessLookupError, ImportError):
                # Processo não existe mais ou erro de importação
                print("🧹 Removendo arquivo de lock órfão...")
                if os.path.exists(LOCKFILE):
                    os.remove(LOCKFILE)
                    
        except (ValueError, FileNotFoundError):
            # Arquivo corrompido, remover
            if os.path.exists(LOCKFILE):
                os.remove(LOCKFILE)
    
    # Criar diretório se não existir
    os.makedirs(os.path.dirname(LOCKFILE), exist_ok=True)
    
    # Criar lock file com PID
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))
    print(f"✅ Lock file criado. PID: {os.getpid()}")

def remove_lockfile():
    """Remove o lock file com verificação adicional."""
    if os.path.exists(LOCKFILE):
        try:
            # Verificar se o PID no arquivo é nosso
            with open(LOCKFILE, "r") as f:
                stored_pid = int(f.read().strip())
            
            if stored_pid == os.getpid():
                os.remove(LOCKFILE)
                print("🧹 Lock file removido com sucesso.")
            else:
                print("⚠️ Lock file pertence a outro processo, não removido.")
        except Exception as e:
            print(f"⚠️ Erro ao remover lock file: {e}")

# Registrar função de limpeza
import atexit
atexit.register(remove_lockfile)

# Tratar sinais para limpeza adequada
def signal_handler(signum, frame):
    print(f"\n🛑 Sinal {signum} recebido. Encerrando bot...")
    remove_lockfile()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ===== DATA MANAGEMENT FUNCTIONS =====
def salvar_dados():
    """Salva dados com proteção contra corrupção."""
    dados = {
        "auto_roles": auto_roles,
        "ticket_response_channels": ticket_response_channels,
        "mention_roles": mention_roles,
        "sugestao_channels": sugestao_channels,
        "ticket_categories": ticket_categories,
        "ticket_support_roles": ticket_support_roles,
    }

    temp_file = "dados_servidor_temp.json"
    final_file = "dados_servidor.json"
    
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        os.replace(temp_file, final_file)
    except Exception as e:
        print(f"⚠️ Erro ao salvar dados: {e}")

def carregar_dados():
    """Carrega dados com tratamento de erro."""
    try:
        if os.path.exists("dados_servidor.json"):
            with open("dados_servidor.json", "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
                if conteudo:
                    dados = json.loads(conteudo)
                    auto_roles.update(dados.get("auto_roles", {}))
                    ticket_response_channels.update(dados.get("ticket_response_channels", {}))
                    mention_roles.update(dados.get("mention_roles", {}))
                    sugestao_channels.update(dados.get("sugestao_channels", {}))
                    ticket_categories.update(dados.get("ticket_categories", {}))
                    ticket_support_roles.update(dados.get("ticket_support_roles", {}))
                    print("✅ Dados carregados com sucesso.")
    except Exception as e:
        print(f"⚠️ Erro ao carregar dados: {e}")

# ===== TICKET SYSTEM (ORIGINAL) =====
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
            await interaction.response.send_message("❌ Não consegui alterar seu apelido (permite o bot modificar nicknames?)", ephemeral=True)
            return

        if not mod_channel:
            await interaction.response.send_message("❌ Nenhum canal configurado para envio de tickets.", ephemeral=True)
            return

        embed = discord.Embed(title="📉 Novo Pedido de Cargo", color=discord.Color.blurple())
        embed.add_field(name="Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="Cargo desejado", value=self.cargo.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        mention = f"<@&{cargo_id}>" if cargo_id else ""

        await mod_channel.send(content=mention, embed=embed)
        await interaction.response.send_message("✅ Pedido enviado com sucesso! Seu apelido foi atualizado.", ephemeral=True)

class TicketButton(Button):
    def __init__(self):
        super().__init__(label="Solicitar cargo", emoji="📬", style=discord.ButtonStyle.secondary, custom_id="ticket_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton())

# ===== TICKET SYSTEM COM CANAIS INDIVIDUAIS =====
class TicketSupportModal(Modal, title="Abrir Ticket de Suporte"):
    assunto = TextInput(label="Assunto", placeholder="Descreva brevemente seu problema", style=TextStyle.short)
    descricao = TextInput(label="Descrição detalhada", placeholder="Explique seu problema em detalhes...", style=TextStyle.paragraph)
    tipo_suporte = TextInput(label="Tipo de Suporte", placeholder="Ex: Técnico, Financeiro, RH, Geral...", style=TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        category_id = ticket_categories.get(guild_id)
        support_role_id = ticket_support_roles.get(guild_id)
        
        if not category_id:
            await interaction.response.send_message("❌ Sistema de tickets não configurado. Contate um administrador.", ephemeral=True)
            return
            
        category = interaction.guild.get_channel(category_id)
        support_role = interaction.guild.get_role(support_role_id) if support_role_id else None
        
        if not category:
            await interaction.response.send_message("❌ Categoria de tickets não encontrada. Contate um administrador.", ephemeral=True)
            return

        # Criar o canal do ticket
        ticket_name = f"ticket-{interaction.user.name.lower().replace(' ', '-')}-{interaction.user.discriminator}"
        
        # Configurar permissões do canal
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }
        
        # Adicionar permissões para o cargo de suporte se configurado
        if support_role:
            overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)

        try:
            ticket_channel = await interaction.guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket de {interaction.user.display_name} - {self.tipo_suporte.value}"
            )
            
            # Criar embed com informações do ticket
            embed = discord.Embed(
                title="🎫 Novo Ticket de Suporte",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Usuário", value=interaction.user.mention, inline=True)
            embed.add_field(name="📝 Assunto", value=self.assunto.value, inline=True)
            embed.add_field(name="🏷️ Tipo", value=self.tipo_suporte.value, inline=True)
            embed.add_field(name="📄 Descrição", value=self.descricao.value, inline=False)
            embed.set_footer(text=f"ID do usuário: {interaction.user.id}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Criar botão para fechar ticket
            close_view = TicketCloseView()
            
            # Mensagem de menção + embed
            mention_text = f"{interaction.user.mention}"
            if support_role:
                mention_text += f" {support_role.mention}"
                
            await ticket_channel.send(
                content=f"{mention_text}\n\n**Olá {interaction.user.mention}!** 👋\nSeu ticket foi criado com sucesso. Nossa equipe irá te ajudar em breve.\n\n**Para fechar este ticket, clique no botão abaixo:**",
                embed=embed,
                view=close_view
            )
            
            await interaction.response.send_message(f"✅ Seu ticket foi criado! Acesse: {ticket_channel.mention}", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para criar canais. Contate um administrador.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao criar ticket: {str(e)}", ephemeral=True)

class TicketSupportButton(Button):
    def __init__(self):
        super().__init__(label="🎫 Abrir Ticket", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="ticket_support_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketSupportModal())

class TicketSupportView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSupportButton())

# ===== SISTEMA PARA FECHAR TICKETS =====
class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="🔒 Fechar Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        # Verificar se é o autor do ticket ou tem permissão de gerenciar canais
        channel_topic = interaction.channel.topic or ""
        user_id = None
        
        # Extrair ID do usuário do tópico ou nome do canal
        if "Ticket de" in channel_topic:
            try:
                # Tentar extrair do footer da primeira mensagem
                async for message in interaction.channel.history(limit=50, oldest_first=True):
                    if message.embeds and message.author == interaction.guild.me:
                        embed = message.embeds[0]
                        if embed.footer and "ID do usuário:" in embed.footer.text:
                            user_id = int(embed.footer.text.split("ID do usuário: ")[1])
                            break
            except:
                pass
        
        # Verificar permissões
        has_permission = (
            interaction.user.id == user_id or 
            interaction.user.guild_permissions.manage_channels or
            any(role.id == ticket_support_roles.get(str(interaction.guild.id)) for role in interaction.user.roles)
        )
        
        if not has_permission:
            await interaction.response.send_message("❌ Você não tem permissão para fechar este ticket.", ephemeral=True)
            return
            
        # Confirmar fechamento
        confirm_view = ConfirmCloseView()
        await interaction.response.send_message("⚠️ Tem certeza que deseja fechar este ticket? **Esta ação não pode ser desfeita.**", view=confirm_view, ephemeral=True)

class ConfirmCloseView(View):
    def __init__(self):
        super().__init__(timeout=30)
        
    @discord.ui.button(label="✅ Sim, fechar", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.send_message("🔒 Fechando ticket em 5 segundos...", ephemeral=True)
            await asyncio.sleep(5)
            await interaction.followup.send("**🎫 Ticket fechado com sucesso!**")
            await asyncio.sleep(2)
            await interaction.channel.delete(reason="Ticket fechado")
        except:
            pass
            
    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
    async def cancel_close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("✅ Fechamento cancelado.", ephemeral=True)

# ===== SUGGESTION/COMPLAINT SYSTEM =====
class SugestaoModal(Modal, title="Envie sua sugestão ou reclamação"):
    mensagem = TextInput(label="Escreva aqui", style=TextStyle.paragraph)

    async def on_submit(self, interaction):
        canal_id = sugestao_channels.get(str(interaction.guild.id))
        canal = bot.get_channel(canal_id)
        if canal:
            embed = discord.Embed(title="📢 Sugestão/Reclamação Anônima", description=self.mensagem.value, color=discord.Color.orange())
            embed.set_footer(text="Enviado anonimamente")
            await canal.send(embed=embed)
        await interaction.response.send_message("✅ Sua mensagem foi enviada de forma anônima!", ephemeral=True)

class SugestaoButton(Button):
    def __init__(self):
        super().__init__(label="Enviar sugestão/reclamação", emoji="💡", style=discord.ButtonStyle.secondary, custom_id="sugestao_button")

    async def callback(self, interaction):
        await interaction.response.send_modal(SugestaoModal())

class SugestaoView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SugestaoButton())

# ===== BOT EVENTS =====
@bot.event
async def on_ready():
    global views_added
    print(f"✅ Bot conectado como {bot.user}")
    
    # Adicionar views apenas uma vez
    if not views_added:
        try:
            bot.add_view(TicketButtonView())
            bot.add_view(SugestaoView())
            bot.add_view(TicketSupportView())
            bot.add_view(TicketCloseView())
            views_added = True
            print("✅ Views adicionadas com sucesso.")
        except Exception as e:
            print(f"⚠️ Erro ao adicionar Views: {e}")
    else:
        print("ℹ️ Views já foram adicionadas anteriormente.")

@bot.event
async def on_member_join(member):
    role_id = auto_roles.get(str(member.guild.id))
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role)
                print(f"✅ Cargo {role.name} atribuído a {member.name}")
            except Exception as e:
                print(f"⚠️ Erro ao atribuir cargo: {e}")

@bot.event
async def on_command_completion(ctx):
    salvar_dados()

@bot.event
async def on_guild_join(guild):
    salvar_dados()

@bot.event
async def on_guild_remove(guild):
    auto_roles.pop(str(guild.id), None)
    ticket_response_channels.pop(str(guild.id), None)
    mention_roles.pop(str(guild.id), None)
    sugestao_channels.pop(str(guild.id), None)
    ticket_categories.pop(str(guild.id), None)
    ticket_support_roles.pop(str(guild.id), None)
    salvar_dados()

# ===== COMMANDS =====
@bot.command(aliases=["cargos"])
@commands.has_permissions(administrator=True)
async def cargo(ctx):
    """Define o cargo automático para novos membros."""
    roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
    options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25] if r.name.strip()]

    if not options:
        await ctx.send("⚠️ Nenhum cargo válido encontrado.")
        return

    class RoleSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Selecione o cargo automático", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_role_id = int(self.values[0])
            auto_roles[str(ctx.guild.id)] = selected_role_id
            salvar_dados()
            role = ctx.guild.get_role(selected_role_id)
            await interaction.response.send_message(f"✅ Cargo automático configurado para: **{role.name}**", ephemeral=True)

    view = View()
    view.add_item(RoleSelect())
    await ctx.send("👥 Selecione o cargo automático:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def setcargo(ctx):
    """Define qual cargo será mencionado nas mensagens do ticket."""
    roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
    options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25] if r.name.strip()]

    if not options:
        await ctx.send("⚠️ Nenhum cargo válido encontrado.")
        return

    class MentionRoleSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Selecione o cargo para mencionar nos tickets", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected = int(self.values[0])
            mention_roles[str(ctx.guild.id)] = selected
            salvar_dados()
            role = ctx.guild.get_role(selected)
            await interaction.response.send_message(f"📌 Cargo a ser mencionado nos tickets definido como: **{role.mention}**", ephemeral=True)

    view = View()
    view.add_item(MentionRoleSelect())
    await ctx.send("🔣 Selecione o cargo que será mencionado nos tickets:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    """Escolhe o canal para os pedidos de cargo e exibe o botão."""
    all_channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
    if not all_channels:
        await ctx.send("❌ Não há canais disponíveis para seleção.")
        return

    per_page = 25
    total_pages = ceil(len(all_channels) / per_page)

    class ChannelSelect(Select):
        def __init__(self, page=0):
            self.page = page
            start = page * per_page
            end = start + per_page
            options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in all_channels[start:end]]
            super().__init__(placeholder=f"Página {page + 1} de {total_pages}", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_channel_id = int(self.values[0])
            ticket_response_channels[str(ctx.guild.id)] = selected_channel_id
            await interaction.response.send_message(f"✅ Canal de envio configurado para <#{selected_channel_id}>.", ephemeral=True)
            await ctx.send("📉 Solicite seu cargo abaixo:", view=TicketButtonView())

    class ChannelSelectionView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.page = 0
            self.select = ChannelSelect(self.page)
            self.add_item(self.select)

            if total_pages > 1:
                self.prev = Button(label="⏪ Anterior", style=discord.ButtonStyle.secondary)
                self.next = Button(label="⏩ Próximo", style=discord.ButtonStyle.secondary)
                self.prev.callback = self.go_prev
                self.next.callback = self.go_next
                self.add_item(self.prev)
                self.add_item(self.next)

        async def go_prev(self, interaction):
            if self.page > 0:
                self.page -= 1
                await self.update(interaction)

        async def go_next(self, interaction):
            if self.page < total_pages - 1:
                self.page += 1
                await self.update(interaction)

        async def update(self, interaction):
            self.clear_items()
            self.select = ChannelSelect(self.page)
            self.add_item(self.select)
            if total_pages > 1:
                self.add_item(self.prev)
                self.add_item(self.next)
            await interaction.response.edit_message(view=self)

    await ctx.send("📌 Selecione o canal para onde os tickets serão enviados:", view=ChannelSelectionView())

@bot.command()
@commands.has_permissions(administrator=True)
async def setupticket(ctx):
    """Configura o sistema de tickets (categoria e cargo de suporte)."""
    guild_id = str(ctx.guild.id)
    
    # Primeiro, selecionar categoria
    categories = ctx.guild.categories
    if not categories:
        await ctx.send("❌ Não há categorias no servidor. Crie uma categoria primeiro.")
        return
        
    category_options = [SelectOption(label=cat.name[:100], value=str(cat.id)) for cat in categories[:25]]
    
    class CategorySelect(Select):
        def __init__(self):
            super().__init__(placeholder="Selecione a categoria para os tickets", options=category_options)
            
        async def callback(self, interaction: discord.Interaction):
            selected_category = int(self.values[0])
            ticket_categories[guild_id] = selected_category
            
            # Agora selecionar o cargo de suporte
            roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
            if not roles:
                await interaction.response.send_message("⚠️ Nenhum cargo encontrado para suporte. Configuração parcial salva.", ephemeral=True)
                salvar_dados()
                return
                
            role_options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]
            
            class SupportRoleSelect(Select):
                def __init__(self):
                    super().__init__(placeholder="Selecione o cargo que pode ver os tickets", options=role_options)
                    
                async def callback(self, role_interaction: discord.Interaction):
                    selected_role = int(self.values[0])
                    ticket_support_roles[guild_id] = selected_role
                    salvar_dados()
                    
                    category = ctx.guild.get_channel(selected_category)
                    role = ctx.guild.get_role(selected_role)
                    
                    await role_interaction.response.send_message(
                        f"✅ Sistema de tickets configurado!\n"
                        f"📁 Categoria: **{category.name}**\n"
                        f"👥 Cargo de suporte: **{role.name}**", 
                        ephemeral=True
                    )
            
            role_view = View()
            role_view.add_item(SupportRoleSelect())
            await interaction.response.send_message("👥 Agora selecione o cargo de suporte:", view=role_view, ephemeral=True)
    
    view = View()
    view.add_item(CategorySelect())
    await ctx.send("📁 Selecione a categoria onde os tickets serão criados:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketpanel(ctx):
    """Cria o painel de tickets no canal atual."""
    guild_id = str(ctx.guild.id)
    
    if guild_id not in ticket_categories:
        await ctx.send("❌ Sistema de tickets não configurado. Use `!setupticket` primeiro.")
        return
        
    embed = discord.Embed(
        title="🎫 Sistema de Suporte",
        description="**Precisa de ajuda?** Clique no botão abaixo para abrir um ticket!\n\n"
                   "✅ **Como funciona:**\n"
                   "• Clique no botão 🎫\n"
                   "• Preencha o formulário\n"
                   "• Um canal privado será criado para você\n"
                   "• Nossa equipe te ajudará no canal\n\n"
                   "⚠️ **Importante:** Use apenas para suporte real. Tickets desnecessários podem resultar em punições.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Sistema de Tickets • Clique no botão para começar")
    
    await ctx.send(embed=embed, view=TicketSupportView())

@bot.command()
@commands.has_permissions(administrator=True)
async def reclamacao(ctx):
    """Cria botão para sugestões/reclamações anônimas."""
    canais = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
    options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in canais[:25]]

    class CanalSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Escolha onde as mensagens anônimas serão enviadas", options=options)

        async def callback(self, interaction):
            canal_id = int(self.values[0])
            sugestao_channels[str(ctx.guild.id)] = canal_id
            await interaction.response.send_message("✅ Canal de destino configurado!", ephemeral=True)
            await ctx.send(
                "**📜 Envie sua sugestão ou reclamação de forma anônima. Ninguém saberá que foi você.**",
                view=SugestaoView()
            )

    view = View()
    view.add_item(CanalSelect())
    await ctx.send("🔹 Escolha o canal que vai receber as sugestões/reclamações:", view=view)

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx):
    """Limpa todas as mensagens do canal."""
    class ConfirmarLimpeza(Button):
        def __init__(self):
            super().__init__(label="Sim, limpar!", style=discord.ButtonStyle.danger)

        async def callback(self, interaction: discord.Interaction):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Apenas o autor do comando pode confirmar.", ephemeral=True)
                return

            for i in range(5, 0, -1):
                await mensagem.edit(content=f"🧹 Limpando em {i} segundos...")
                await asyncio.sleep(1)

            await ctx.channel.purge()
            aviso = await ctx.send("✅ Todas as mensagens foram limpas com sucesso!")
            await asyncio.sleep(3)
            await aviso.delete()

    view = View()
    view.add_item(ConfirmarLimpeza())
    mensagem = await ctx.send("⚠️ Tem certeza que deseja limpar todas as mensagens deste canal?", view=view)

@bot.command()
async def ping(ctx):
    """Verifica se o bot está funcional e mostra o ping."""
    await ctx.send(f"🏓 Pong! Latência: `{round(bot.latency * 1000)}ms`")

@bot.command(name="ajuda")
async def ajuda(ctx):
    """Mostra a lista de comandos disponíveis."""
    embed = discord.Embed(
        title="📖 Comandos disponíveis",
        color=discord.Color.green(),
        description="Veja abaixo os comandos que você pode usar:"
    )
    embed.add_field(name="!cargo", value="Define o cargo automático para novos membros.", inline=False)
    embed.add_field(name="!ticket", value="Escolhe o canal para os pedidos de cargo e exibe o botão.", inline=False)
    embed.add_field(name="!setcargo", value="Define qual cargo será mencionado nas mensagens do ticket.", inline=False)
    embed.add_field(name="!setupticket", value="Configura o sistema de tickets (categoria e cargo de suporte).", inline=False)
    embed.add_field(name="!ticketpanel", value="Cria o painel de tickets no canal atual.", inline=False)
    embed.add_field(name="!reclamacao", value="Cria botão para sugestões/reclamações anônimas.", inline=False)
    embed.add_field(name="!clear", value="Limpa todas as mensagens do canal atual.", inline=False)
    embed.add_field(name="!ping", value="Verifica se o bot está funcional e mostra o ping.", inline=False)
    embed.add_field(name="!ajuda", value="Mostra esta lista de comandos disponíveis.", inline=False)
    embed.add_field(name="!status", value="Verifica o status do bot e se há múltiplas instâncias.", inline=False)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def status(ctx):
    """Verifica o status do bot e informações do processo."""
    embed = discord.Embed(
        title="🤖 Status do Bot",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    # Informações básicas
    embed.add_field(name="📊 Status", value="✅ Online", inline=True)
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🆔 PID", value=str(os.getpid()), inline=True)
    
    # Informações do servidor
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Usuários", value=len(bot.users), inline=True)
    embed.add_field(name="📋 Views Ativas", value="✅ Carregadas" if views_added else "❌ Não carregadas", inline=True)
    
    # Verificar lock file
    lock_status = "🔒 Ativo" if os.path.exists(LOCKFILE) else "❌ Não encontrado"
    embed.add_field(name="🔐 Lock File", value=lock_status, inline=True)
    
    # Informações de configuração do servidor atual
    guild_id = str(ctx.guild.id)
    configs = []
    
    if guild_id in auto_roles:
        role = ctx.guild.get_role(auto_roles[guild_id])
        configs.append(f"• Cargo automático: {role.name if role else 'Cargo não encontrado'}")
    
    if guild_id in ticket_categories:
        category = ctx.guild.get_channel(ticket_categories[guild_id])
        configs.append(f"• Categoria tickets: {category.name if category else 'Categoria não encontrada'}")
    
    if guild_id in ticket_response_channels:
        channel = bot.get_channel(ticket_response_channels[guild_id])
        configs.append(f"• Canal tickets: {channel.name if channel else 'Canal não encontrado'}")
    
    if guild_id in sugestao_channels:
        channel = bot.get_channel(sugestao_channels[guild_id])
        configs.append(f"• Canal sugestões: {channel.name if channel else 'Canal não encontrado'}")
    
    config_text = "\n".join(configs) if configs else "Nenhuma configuração ativa"
    embed.add_field(name="⚙️ Configurações do Servidor", value=config_text, inline=False)
    
    embed.set_footer(text=f"Bot iniciado em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def forceunlock(ctx):
    """Remove o lock file manualmente (use apenas se necessário)."""
    if os.path.exists(LOCKFILE):
        try:
            os.remove(LOCKFILE)
            await ctx.send("✅ Lock file removido com sucesso.")
        except Exception as e:
            await ctx.send(f"❌ Erro ao remover lock file: {e}")
    else:
        await ctx.send("ℹ️ Nenhum lock file encontrado.")

# ===== ERROR HANDLING =====
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar este comando.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignorar comandos não encontrados
    else:
        print(f"Erro no comando {ctx.command}: {error}")
        await ctx.send("❌ Ocorreu um erro ao executar o comando.")

# ===== MAIN =====
if __name__ == "__main__":
    try:
        # Verificar se já existe uma instância rodando
        check_lock_file()
        
        # Carregar dados salvos
        carregar_dados()
        
        # Carregar token
        load_dotenv()
        TOKEN = os.getenv("DISCORD_TOKEN")
        
        if not TOKEN:
            print("❌ Token do Discord não encontrado no arquivo .env")
            sys.exit(1)
        
        print("🚀 Iniciando bot...")
        bot.run(TOKEN)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário.")
        remove_lockfile()
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        remove_lockfile()
        sys.exit(1)
    finally:
        remove_lockfile()
