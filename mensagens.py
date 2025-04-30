import discord
from discord.ext import commands
from discord.ui import Modal, View, Button, Select, TextInput
from discord import TextStyle, SelectOption
from datetime import datetime
import json
import os

tipos_mensagem = {}

def carregar_tipos_mensagem():
    global tipos_mensagem
    if os.path.exists("tipos_mensagem.json"):
        with open("tipos_mensagem.json", "r", encoding="utf-8") as f:
            tipos_mensagem = json.load(f)
    else:
        tipos_mensagem.update({
            "aviso": {"emoji": "⚠️", "cor": "#f1c40f"},
            "informacao": {"emoji": "ℹ️", "cor": "#3498db"},
            "aviso_importante": {"emoji": "🚨", "cor": "#e74c3c"},
            "desligamento": {"emoji": "🏴", "cor": "#7f8c8d"},
            "contratacao": {"emoji": "🟢", "cor": "#2ecc71"}
        })
        salvar_tipos_mensagem()

def salvar_tipos_mensagem():
    with open("tipos_mensagem.json", "w", encoding="utf-8") as f:
        json.dump(tipos_mensagem, f, indent=4, ensure_ascii=False)

def setup_mensagens_commands(bot):

    @bot.command()
    async def ping(ctx):
        await ctx.send(f"🏓 Pong! Latência: `{round(bot.latency * 1000)}ms`")

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def clear(ctx):
        class Confirmar(Button):
            def __init__(self):
                super().__init__(label="Sim, limpar!", style=discord.ButtonStyle.danger)

            async def callback(self, interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("❌ Apenas o autor pode confirmar.", ephemeral=True)
                    return

                for i in range(5, 0, -1):
                    await mensagem.edit(content=f"🧹 Limpando em {i} segundos...")
                    await discord.utils.sleep_until(datetime.now().replace(second=0, microsecond=0) + timedelta(seconds=i))
                await ctx.channel.purge()
                aviso = await ctx.send("✅ Limpeza concluída.")
                await discord.utils.sleep_until(datetime.now() + timedelta(seconds=3))
                await aviso.delete()

        view = View()
        view.add_item(Confirmar())
        mensagem = await ctx.send("⚠️ Tem certeza que deseja limpar todas as mensagens deste canal?", view=view)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def tipos(ctx):
        if not tipos_mensagem:
            await ctx.send("⚠️ Nenhum tipo de mensagem cadastrado.")
            return

        embed = discord.Embed(title="📚 Tipos de Mensagem Cadastrados", color=discord.Color.blue())
        for tipo, info in tipos_mensagem.items():
            embed.add_field(
                name=f"{info.get('emoji', '📝')} {tipo.replace('_', ' ').title()}",
                value=f"**Cor:** {info.get('cor', '#3498db')} ",
                inline=False
            )
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def criartipo(ctx):
        class CriarTipoModal(Modal, title="Criar Novo Tipo"):
            nome = TextInput(label="Nome", placeholder="Ex: Aviso Urgente")
            emoji = TextInput(label="Emoji", placeholder="Ex: 🚨")
            cor = TextInput(label="Cor (hex)", placeholder="Ex: #ff0000")

            async def on_submit(self, interaction):
                tipo_id = self.nome.value.strip().lower().replace(" ", "_")
                tipos_mensagem[tipo_id] = {
                    "emoji": self.emoji.value.strip(),
                    "cor": self.cor.value.strip()
                }
                salvar_tipos_mensagem()
                await interaction.response.send_message(f"✅ Tipo `{self.nome.value}` criado com sucesso!", ephemeral=True)

        view = View()
        view.add_item(Button(label="Criar Novo Tipo", style=discord.ButtonStyle.primary,
                             custom_id="criartipo_btn"))

        @bot.event
        async def on_interaction(interaction):
            if interaction.data.get("custom_id") == "criartipo_btn":
                await interaction.response.send_modal(CriarTipoModal())

        await ctx.send("➕ Clique abaixo para criar um novo tipo de mensagem:", view=view)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def apagatipo(ctx):
        if not tipos_mensagem:
            await ctx.send("⚠️ Nenhum tipo de mensagem cadastrado.")
            return

        options = [SelectOption(label=tipo.replace("_", " ").title(), value=tipo) for tipo in tipos_mensagem]

        class TipoSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Selecione o tipo para apagar", options=options)

            async def callback(self, interaction):
                tipo = self.values[0]
                tipos_mensagem.pop(tipo, None)
                salvar_tipos_mensagem()
                await interaction.response.send_message(f"🗑️ Tipo `{tipo.replace('_', ' ').title()}` apagado.", ephemeral=True)

        view = View()
        view.add_item(TipoSelect())
        await ctx.send("🗑️ Selecione o tipo que deseja remover:", view=view)

    @bot.command()
    async def ajuda(ctx):
        embed = discord.Embed(
            title="📖 Comandos disponíveis",
            color=discord.Color.green(),
            description="Veja abaixo os comandos que você pode usar:"
        )
        comandos = {
            "!cargo": "Define o cargo automático.",
            "!ticket": "Canal de pedidos de cargo.",
            "!setcargo": "Define o cargo mencionado em tickets.",
            "!reclamacao": "Sugestões/reclamações anônimas.",
            "!setcargomensagem": "Define quem pode usar !mensagem.",
            "!removecargomensagem": "Remove permissões de !mensagem.",
            "!mensagem": "Cria mensagens com tipos e menções.",
            "!tipos": "Lista os tipos de mensagem.",
            "!criartipo": "Cria um novo tipo.",
            "!apagatipo": "Remove um tipo existente.",
            "!ping": "Verifica se o bot está online."
        }
        for cmd, desc in comandos.items():
            embed.add_field(name=cmd, value=desc, inline=False)
        await ctx.send(embed=embed)
