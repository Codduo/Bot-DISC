import discord
from discord.ext import commands
from discord import TextStyle
from discord.ui import View, Modal, TextInput, Button
import json
import os

sugestao_channels = {}

def carregar_dados():
    if os.path.exists("dados_servidor.json"):
        with open("dados_servidor.json", "r", encoding="utf-8") as f:
            dados = json.loads(f.read().strip())
            sugestao_channels.update(dados.get("sugestao_channels", {}))

def salvar_dados(dados_sugestao=None):
    if dados_sugestao is not None:
        sugestao_channels.update(dados_sugestao)
    
    if os.path.exists("dados_servidor.json"):
        with open("dados_servidor.json", "r", encoding="utf-8") as f:
            dados = json.loads(f.read().strip())
    else:
        dados = {}
    
    dados["sugestao_channels"] = sugestao_channels
    
    temp_file = "dados_servidor_temp.json"
    final_file = "dados_servidor.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    os.replace(temp_file, final_file)

class SugestaoModal(Modal, title="Envie sua sugestão ou reclamação"):
    mensagem = TextInput(label="Escreva aqui", style=TextStyle.paragraph)

    async def on_submit(self, interaction):
        canal_id = sugestao_channels.get(str(interaction.guild.id))
        canal = interaction.client.get_channel(canal_id)
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

def setup(bot):
    carregar_dados()
    
    @bot.command()
    @commands.has_permissions(administrator=True)
    async def reclamacao(ctx):
        canais = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
        
        from discord import SelectOption
        options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in canais[:25]]

        class CanalSelect(discord.ui.Select):
            def __init__(self):
                super().__init__(placeholder="Escolha onde as mensagens anônimas serão enviadas", options=options)

            async def callback(self, interaction):
                canal_id = int(self.values[0])
                sugestao_channels[str(ctx.guild.id)] = canal_id
                salvar_dados()
                await interaction.response.send_message("✅ Canal de destino configurado!", ephemeral=True)
                await ctx.send(
                    "**📜 Envie sua sugestão ou reclamação de forma anônima. Ninguém saberá que foi você.**",
                    view=SugestaoView()
                )

        view = View()
        view.add_item(CanalSelect())
        await ctx.send("🔹 Escolha o canal que vai receber as sugestões/reclamações:", view=view)

    bot.add_view(SugestaoView())