import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button, Select
from discord import SelectOption
from math import ceil

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Armazenamento por servidor (guild_id)
auto_roles = {}
ticket_response_channels = {}
mention_roles = {}  # guild_id: cargo que será mencionado nos tickets


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")


# Aplica o cargo automático ao novo membro
@bot.event
async def on_member_join(member):
    role_id = auto_roles.get(member.guild.id)
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            print(f"✅ Cargo {role.name} atribuído a {member.name}")


# Comando: define o cargo automático
@bot.command(aliases=["cargos"])
@commands.has_permissions(administrator=True)
async def cargo(ctx):
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
            auto_roles[ctx.guild.id] = selected_role_id
            role = ctx.guild.get_role(selected_role_id)
            await interaction.response.send_message(
                f"✅ Cargo automático configurado para: **{role.name}**", ephemeral=True
            )

    view = View()
    view.add_item(RoleSelect())
    await ctx.send("👥 Selecione o cargo automático:", view=view)


# Comando: define o cargo a ser mencionado nos tickets
@bot.command()
@commands.has_permissions(administrator=True)
async def setcargo(ctx):
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
            mention_roles[ctx.guild.id] = selected
            role = ctx.guild.get_role(selected)
            await interaction.response.send_message(
                f"📌 Cargo a ser mencionado nos tickets definido como: **{role.mention}**", ephemeral=True
            )

    view = View()
    view.add_item(MentionRoleSelect())
    await ctx.send("📣 Selecione o cargo que será mencionado nos tickets:", view=view)



# Modal que abre com o botão
class TicketModal(Modal, title="Solicitar Cargo"):
    nome = TextInput(label="Nome", placeholder="Digite seu nome completo", style=discord.TextStyle.short)
    cargo = TextInput(label="Setor / Cargo desejado", placeholder="Ex: Financeiro, RH...", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        mod_channel_id = ticket_response_channels.get(interaction.guild.id)
        mod_channel = bot.get_channel(mod_channel_id)
        cargo_id = mention_roles.get(interaction.guild.id)

        # Atualiza apelido
        try:
            await interaction.user.edit(nick=self.nome.value)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não consegui alterar seu apelido (permite o bot modificar nicknames?)", ephemeral=True)
            return

        if not mod_channel:
            await interaction.response.send_message("❌ Nenhum canal configurado para envio de tickets.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📩 Novo Pedido de Cargo",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="Cargo desejado", value=self.cargo.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        mention = f"<@&{cargo_id}>" if cargo_id else ""

        await mod_channel.send(content=mention, embed=embed)
        await interaction.response.send_message("✅ Pedido enviado com sucesso! Seu apelido foi atualizado.", ephemeral=True)



# Botão para solicitar cargo
class TicketButton(Button):
    def __init__(self):
        super().__init__(label="Solicitar cargo", emoji="📬", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())


class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton())


# Comando: configura o canal onde os tickets serão enviados
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
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
            options = [
                SelectOption(label=c.name[:100], value=str(c.id)) for c in all_channels[start:end]
            ]
            super().__init__(placeholder=f"Página {page + 1} de {total_pages}", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_channel_id = int(self.values[0])
            ticket_response_channels[ctx.guild.id] = selected_channel_id
            await interaction.response.send_message(
                f"✅ Canal de envio configurado para <#{selected_channel_id}>.",
                ephemeral=True
            )
            await ctx.send("📩 Solicite seu cargo abaixo:", view=TicketButtonView())

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


# Comando de ajuda
@bot.command(name="ajuda")
async def ajuda(ctx):
    embed = discord.Embed(
        title="📖 Comandos disponíveis",
        color=discord.Color.green(),
        description="Veja abaixo os comandos que você pode usar:"
    )
    embed.add_field(name="!cargo", value="Define o cargo automático que novos membros recebem.", inline=False)
    embed.add_field(name="!ticket", value="Escolhe o canal para envio dos pedidos de cargo + ativa o botão de solicitação.", inline=False)
    embed.add_field(name="!setcargo", value="Define qual cargo será mencionado nas mensagens de ticket.", inline=False)
    embed.add_field(name="!ajuda", value="Mostra essa mensagem com todos os comandos disponíveis.", inline=False)

    await ctx.send(embed=embed)


# INÍCIO DO BOT
TOKEN = "MTM2MTM4MzI4MDIwODc3NzQ2Nw.GAmU1k.76LesPY9Dw1u6Ab6PW9nMhlIsru0eHG1z0ZR3c"
bot.run(TOKEN)
