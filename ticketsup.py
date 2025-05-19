import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Abrir Ticket de Suporte", style=discord.ButtonStyle.green, custom_id="abrir_ticket_suporte"))

class TicketSuporte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ouvinte do botão
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") != "abrir_ticket_suporte":
            return

        await interaction.response.send_message("Por favor, descreva o problema que está enfrentando:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=300)
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado. Tente novamente mais tarde.", ephemeral=True)
            return

        guild = interaction.guild
        author = interaction.user
        channel_name = f"suporte-{author.name}".replace(" ", "-").lower()

        # Cargo de suporte
        suporte_role = discord.utils.get(guild.roles, name="Suporte Técnico")
        if not suporte_role:
            await interaction.followup.send("Cargo 'Suporte Técnico' não encontrado.", ephemeral=True)
            return

        # Permissões
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            suporte_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        canal = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Ticket de suporte aberto por {author.name}"
        )

        await canal.send(f"Olá {author.mention}, nosso time de suporte vai te atender.\n\n📩 **Mensagem inicial:**\n{msg.content}")
        await interaction.followup.send(f"Seu ticket foi criado: {canal.mention}", ephemeral=True)

# Registro do cog
async def setup(bot):
    await bot.add_cog(TicketSuporte(bot))
