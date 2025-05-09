import discord
from discord.ext import commands
from discord import TextStyle
from discord.ui import View, Modal, TextInput, Button, Select
from discord import SelectOption
from math import ceil

class TicketModal(Modal, title="Solicitar Cargo"):
    nome = TextInput(label="Nome", placeholder="Digite seu nome completo", style=TextStyle.short)
    cargo = TextInput(label="Setor / Cargo desejado", placeholder="Ex: Financeiro, RH...", style=TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        from bot import ticket_response_channels, mention_roles, bot
        
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

class TicketCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ticket(self, ctx):
        from bot import ticket_response_channels, salvar_dados
        
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
                salvar_dados()
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

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setcargo(self, ctx):
        from bot import mention_roles, salvar_dados
        
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

def setup(bot):
    bot.add_cog(TicketCommands(bot))