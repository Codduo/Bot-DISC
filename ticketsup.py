import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir Ticket de Suporte", style=discord.ButtonStyle.green, custom_id="open_ticket")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Por favor, descreva o problema que está enfrentando:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for('message', check=check, timeout=300)  # 5 minutos
        except asyncio.TimeoutError:
            await interaction.followup.send("Tempo esgotado. Por favor, tente novamente.", ephemeral=True)
            return

        guild = interaction.guild
        author = interaction.user
        channel_name = f"suporte-{author.name}".replace(" ", "-").lower()

        existing = discord.utils.get(guild.channels, name=channel_name)
        if existing:
            await interaction.followup.send(f"Você já possui um ticket aberto: {existing.mention}", ephemeral=True)
            return

        suporte_role = discord.utils.get(guild.roles, name="Suporte Técnico Kommo")

        if not suporte_role:
            await interaction.followup.send("Cargo 'Suporte Técnico Kommo", ephemeral=True)
            return

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

        await canal.send(f"Olá {author.mention}, obrigado por entrar em contato com o suporte.\n\n**Descrição do problema:**\n{msg.content}")
        await interaction.followup.send(f"Seu ticket foi criado com sucesso: {canal.mention}", ephemeral=True)

async def setup(bot):
    await bot.wait_until_ready()
    channel_id = 1360233305592823929
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send("Clique no botão abaixo para abrir um ticket de suporte:", view=TicketView())
