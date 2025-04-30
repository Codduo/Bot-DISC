from discord.ext import commands
from discord.ui import Modal, TextInput
from discord import TextStyle, Embed, Color
from dados.salvar import carregar_aniversarios, salvar_aniversarios
from config import CANAL_ANIVERSARIO_ID
from datetime import datetime


def setup(bot):

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def adicionar_aniversario(ctx):
        class AdicionarAniversarioModal(Modal, title="Adicionar Aniversariante"):
            user_id = TextInput(label="ID do Usuário", placeholder="Ex: 1234567890", style=TextStyle.short)
            nome = TextInput(label="Nome", placeholder="Ex: João Silva", style=TextStyle.short)
            data_nascimento = TextInput(label="Data de Nascimento (YYYY-MM-DD)", placeholder="Ex: 2000-03-01", style=TextStyle.short)
            link_foto = TextInput(label="Link da Foto (Google Drive)", placeholder="https://...", style=TextStyle.short)

            async def on_submit(self, interaction):
                user_id = self.user_id.value.strip()
                nome = self.nome.value.strip()
                data_nascimento = self.data_nascimento.value.strip()
                link_foto = self.link_foto.value.strip()

                try:
                    datetime.strptime(data_nascimento, "%Y-%m-%d")
                except ValueError:
                    await interaction.response.send_message("⚠️ Data inválida. Use YYYY-MM-DD.", ephemeral=True)
                    return

                aniversarios = carregar_aniversarios()
                aniversarios[user_id] = {
                    "nome": nome,
                    "data_nascimento": data_nascimento,
                    "link_foto": link_foto
                }
                salvar_aniversarios(aniversarios)
                await interaction.response.send_message(f"✅ Aniversariante {nome} adicionado!", ephemeral=True)

        await ctx.send("📅 Preencha as informações:", view=AdicionarAniversarioModal())


    @bot.command()
    @commands.has_permissions(administrator=True)
    async def simular_aniversario(ctx, user_id: int):
        aniversarios = carregar_aniversarios()
        info = aniversarios.get(str(user_id))
        if not info:
            await ctx.send(f"⚠️ ID {user_id} não encontrado.")
            return

        canal = ctx.bot.get_channel(CANAL_ANIVERSARIO_ID)
        link_imagem = info.get("link_foto")

        membro = ctx.guild.get_member(user_id)
        if membro and link_imagem:
            mention = f"{membro.mention} <@&1359579655702839458>"
            embed = Embed(title=f"🎉🎂 Feliz Aniversário, {info['nome']}! 🎂🎉", color=Color.blurple())
            embed.set_image(url=link_imagem)
            await canal.send(mention, embed=embed)
            await ctx.send(f"✅ Simulação enviada para {info['nome']}.")
        else:
            await ctx.send("⚠️ Membro não encontrado ou imagem ausente.")
