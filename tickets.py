import discord
from discord.ext import commands
from discord.ui import Modal, View, Button, Select, TextInput
from discord import TextStyle, SelectOption
from math import ceil

ticket_response_channels = {}
sugestao_channels = {}

def setup_tickets_commands(bot):

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def ticket(ctx):
        all_channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
        if not all_channels:
            await ctx.send("❌ Nenhum canal disponível.")
            return

        per_page = 25
        total_pages = ceil(len(all_channels) / per_page)

        class ChannelSelect(Select):
            def __init__(self, page=0):
                self.page = page
                start = page * per_page
                end = start + per_page
                options = [
                    SelectOption(label=c.name[:100], value=str(c.id))
                    for c in all_channels[start:end]
                ]
                super().__init__(placeholder=f"Página {page + 1} de {total_pages}", options=options)

            async def callback(self, interaction):
                ticket_response_channels[str(ctx.guild.id)] = int(self.values[0])
                await interaction.response.send_message("✅ Canal configurado!", ephemeral=True)
                await ctx.send("📥 Solicite seu cargo abaixo:", view=TicketButtonView())

        class ChannelView(View):
            def __init__(self):
                super().__init__(timeout=60)
                self.page = 0
                self.select = ChannelSelect(self.page)
                self.add_item(self.select)
                if total_pages > 1:
                    self.prev = Button(label="⏪ Anterior")
                    self.next = Button(label="⏩ Próximo")
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

        await ctx.send("📌 Selecione o canal para os tickets:", view=ChannelView())

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def reclamacao(ctx):
        canais = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
        options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in canais[:25]]

        class CanalSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Escolha o canal", options=options)

            async def callback(self, interaction):
                sugestao_channels[str(ctx.guild.id)] = int(self.values[0])
                await interaction.response.send_message("✅ Canal de destino configurado!", ephemeral=True)
                await ctx.send(
                    "**📜 Envie sua sugestão ou reclamação de forma anônima. Ninguém saberá que foi você.**",
                    view=SugestaoView()
                )

        view = View()
        view.add_item(CanalSelect())
        await ctx.send("🔹 Escolha o canal para sugestões:", view=view)

class TicketModal(Modal, title="Solicitar Cargo"):
    nome = TextInput(label="Nome", placeholder="Seu nome completo", style=TextStyle.short)
    cargo = TextInput(label="Setor / Cargo", placeholder="Ex: RH, Financeiro...", style=TextStyle.paragraph)

    async def on_submit(self, interaction):
        from .cargos import mention_roles  # Importa localmente para evitar dependência circular
        mod_channel_id = ticket_response_channels.get(str(interaction.guild.id))
        mod_channel = interaction.client.get_channel(mod_channel_id)
        cargo_id = mention_roles.get(str(interaction.guild.id))

        try:
            await interaction.user.edit(nick=self.nome.value)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão para mudar o apelido.", ephemeral=True)
            return

        if not mod_channel:
            await interaction.response.send_message("❌ Nenhum canal configurado para tickets.", ephemeral=True)
            return

        embed = discord.Embed(title="📨 Pedido de Cargo", color=discord.Color.blurple())
        embed.add_field(name="Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="Cargo desejado", value=self.cargo.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        mention = f"<@&{cargo_id}>" if cargo_id else ""
        await mod_channel.send(content=mention, embed=embed)
        await interaction.response.send_message("✅ Pedido enviado! Apelido atualizado.", ephemeral=True)

class TicketButton(Button):
    def __init__(self):
        super().__init__(label="Solicitar cargo", emoji="📬", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction):
        await interaction.response.send_modal(TicketModal())

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton())

class SugestaoModal(Modal, title="Sugestão/Reclamação"):
    mensagem = TextInput(label="Escreva sua mensagem", style=TextStyle.paragraph)

    async def on_submit(self, interaction):
        canal_id = sugestao_channels.get(str(interaction.guild.id))
        canal = interaction.client.get_channel(canal_id)
        if canal:
            embed = discord.Embed(title="💬 Mensagem Anônima", description=self.mensagem.value, color=discord.Color.orange())
            embed.set_footer(text="Enviado anonimamente")
            await canal.send(embed=embed)
        await interaction.response.send_message("✅ Enviado com sucesso!", ephemeral=True)

class SugestaoButton(Button):
    def __init__(self):
        super().__init__(label="Enviar sugestão/reclamação", emoji="💡", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction):
        await interaction.response.send_modal(SugestaoModal())

class SugestaoView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SugestaoButton())
