import discord
from discord.ext import commands
from discord import TextStyle
from discord.ui import View, Modal, TextInput, Button, Select
from discord import SelectOption
import asyncio
from datetime import datetime

# Importar dados do utils
from utils import (
    salvar_dados, auto_roles, ticket_response_channels, mention_roles,
    sugestao_channels, ticket_categories, ticket_support_roles,
    SUPPORT_TYPES, get_support_type_info, get_all_support_types
)

# ===== TICKET MODAL (PEDIDOS DE CARGO) =====
class TicketModal(Modal, title="Solicitar Cargo"):
    nome = TextInput(label="Nome", placeholder="Digite seu nome completo", style=TextStyle.short)
    cargo = TextInput(label="Setor / Cargo desejado", placeholder="Ex: Financeiro, RH...", style=TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        mod_channel_id = ticket_response_channels.get(str(interaction.guild.id))
        mod_channel = interaction.guild.get_channel(mod_channel_id)
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
        support_info = get_support_type_info(support_type)
        self.title = f"Ticket - {support_info['name']}"

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
        support_info = get_support_type_info(self.support_type)
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
        for key, info in get_all_support_types().items():
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
        support_role_ids = [info['role_id'] for info in get_all_support_types().values()]
        has_permission = (
            interaction.user.id == user_id or 
            interaction.user.guild_permissions.manage_channels or
            any(role.id in support_role_ids for role in interaction.user.roles)
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
        canal = interaction.guild.get_channel(canal_id)
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

# ===== TICKET COMMANDS =====
def setup_ticket_commands(bot):
    """Configura todos os comandos relacionados a tickets."""
    
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

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setupticket(ctx):
        """Configura o sistema de tickets."""
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