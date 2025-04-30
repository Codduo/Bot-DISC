from discord.ui import Modal, TextInput, Button, View
from discord import TextStyle, Interaction, Embed, Color
from dados.salvar import sugestao_channels

class SugestaoModal(Modal, title="Envie sua sugestão ou reclamação"):
    mensagem = TextInput(label="Escreva aqui", style=TextStyle.paragraph)

    async def on_submit(self, interaction: Interaction):
        canal_id = sugestao_channels.get(str(interaction.guild.id))
        canal = interaction.guild.get_channel(canal_id)
        if canal:
            embed = Embed(
                title="📢 Sugestão/Reclamação Anônima",
                description=self.mensagem.value,
                color=Color.orange()
            )
            embed.set_footer(text="Enviado anonimamente")
            await canal.send(embed=embed)
        await interaction.response.send_message("✅ Sua mensagem foi enviada anonimamente!", ephemeral=True)

class SugestaoButton(Button):
    def __init__(self):
        super().__init__(label="Enviar sugestão/reclamação", emoji="💡", style=Button.style.secondary, custom_id="sugestao_button")

    async def callback(self, interaction: Interaction):
        await interaction.response.send_modal(SugestaoModal())

class SugestaoView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SugestaoButton())
