import discord
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View, TextStyle

class SuporteModal(Modal, title="Abrir Suporte Técnico"):
    mensagem = TextInput(label="Descreva o problema", style=TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        author = interaction.user
        suporte_role = discord.utils.get(guild.roles, name="Suporte Técnico")  # ajuste se quiser usar ID

        if not suporte_role:
            await interaction.response.send_message("❌ Cargo 'Suporte Técnico' não encontrado.", ephemeral=True)
            return

        canal_nome = f"suporte-{author.name}".replace(" ", "-").lower()
        existente = discord.utils.get(guild.text_channels, name=canal_nome)
        if existente:
            await interaction.response.send_message(f"📌 Você já tem um ticket aberto: {existente.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            suporte_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        canal = await guild.create_text_channel(name=canal_nome, overwrites=overwrites)
        await canal.send(f"🛠 **Novo ticket de {author.mention}**\n\n📄 {self.mensagem.value}")
        await interaction.response.send_message(f"✅ Ticket criado com sucesso: {canal.mention}", ephemeral=True)

class SuporteButton(Button):
    def __init__(self):
        super().__init__(label="Suporte Técnico", style=discord.ButtonStyle.primary, emoji="🛠", custom_id="botao_suporte")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SuporteModal())

class SuporteView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SuporteButton())

class TicketSuporte(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="botao_suporte")
    @commands.has_permissions(administrator=True)
    async def enviar_botao_suporte(self, ctx):
        await ctx.send("📨 Clique no botão abaixo para abrir um ticket de suporte:", view=SuporteView())

async def setup(bot):
    await bot.add_cog(TicketSuporte(bot))
