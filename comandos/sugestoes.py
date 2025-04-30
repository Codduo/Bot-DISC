from discord.ext import commands
from discord.ui import View, Select
from discord import SelectOption, Interaction, Embed, Color
from dados.salvar import sugestao_channels
from modelos.sugestao import SugestaoView


def setup(bot):

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def reclamacao(ctx):
        canais = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
        options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in canais[:25]]

        if not options:
            await ctx.send("❌ Nenhum canal disponível.")
            return

        class CanalSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Escolha o canal para mensagens anônimas", options=options)

            async def callback(self, interaction: Interaction):
                canal_id = int(self.values[0])
                sugestao_channels[str(ctx.guild.id)] = canal_id
                await interaction.response.send_message("✅ Canal configurado!", ephemeral=True)
                await ctx.send("**📜 Envie sua sugestão ou reclamação de forma anônima.**", view=SugestaoView())

        view = View()
        view.add_item(CanalSelect())
        await ctx.send("🔹 Escolha o canal para sugestões/reclamações:", view=view)
