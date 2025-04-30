import discord
from discord.ext import commands
from discord.ui import Modal, TextInput
from discord import TextStyle
from datetime import datetime
import json
import os

CANAL_ANIVERSARIO_ID = 1362040456279621892

def carregar_aniversarios():
    if os.path.exists("aniversarios.json"):
        with open("aniversarios.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_aniversarios(aniversarios):
    with open("aniversarios.json", "w", encoding="utf-8") as f:
        json.dump(aniversarios, f, indent=4, ensure_ascii=False)

async def verificar_aniversarios(bot):
    aniversarios = carregar_aniversarios()
    hoje = datetime.now().strftime("%m-%d")
    canal = bot.get_channel(CANAL_ANIVERSARIO_ID)

    for user_id, info in aniversarios.items():
        if datetime.strptime(info["data_nascimento"], "%Y-%m-%d").strftime("%m-%d") == hoje:
            guild = bot.get_guild(1359193389022707823)
            membro = guild.get_member(int(user_id)) if guild else None

            if membro and info.get("link_foto"):
                mention = f"{membro.mention} <@&1359579655702839458>"
                embed = discord.Embed(
                    title=f"🎉🎂 **Feliz Aniversário, {info['nome']}!** 🎂🎉",
                    description="🎁 Que seu dia seja repleto de alegrias e conquistas! 💐🎉\n\n🎈 **Parabéns!** 🎈",
                    color=discord.Color.blurple()
                )
                embed.set_image(url=info["link_foto"])
                await canal.send(mention, embed=embed)

async def verificar_diariamente(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            await verificar_aniversarios(bot)
        await discord.utils.sleep_until(datetime(now.year, now.month, now.day, now.hour, now.minute + 1))

def setup_aniversarios_commands(bot):

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def adicionar_aniversario(ctx):
        class AniversarioModal(Modal, title="Adicionar Aniversariante"):
            user_id = TextInput(label="ID do Usuário", placeholder="123...", style=TextStyle.short)
            nome = TextInput(label="Nome", placeholder="João Silva", style=TextStyle.short)
            data = TextInput(label="Data (YYYY-MM-DD)", placeholder="2000-03-01", style=TextStyle.short)
            foto = TextInput(label="Link da Foto", placeholder="https://...", style=TextStyle.short)

            async def on_submit(self, interaction):
                try:
                    datetime.strptime(self.data.value.strip(), "%Y-%m-%d")
                except ValueError:
                    await interaction.response.send_message("⚠️ Data inválida.", ephemeral=True)
                    return

                aniversarios = carregar_aniversarios()
                aniversarios[self.user_id.value.strip()] = {
                    "nome": self.nome.value.strip(),
                    "data_nascimento": self.data.value.strip(),
                    "link_foto": self.foto.value.strip()
                }
                salvar_aniversarios(aniversarios)
                await interaction.response.send_message(f"✅ {self.nome.value.strip()} adicionado!", ephemeral=True)

        await ctx.send("📅 Preencha as informações do aniversariante:", view=AniversarioModal())

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def simular_aniversario(ctx, user_id: int):
        aniversarios = carregar_aniversarios()
        info = aniversarios.get(str(user_id))

        if not info:
            await ctx.send("⚠️ Usuário não encontrado.")
            return

        canal = bot.get_channel(CANAL_ANIVERSARIO_ID)
        guild = bot.get_guild(1359193389022707823)
        membro = guild.get_member(user_id)

        if membro and info.get("link_foto"):
            mention = f"{membro.mention} <@&1359579655702839458>"
            embed = discord.Embed(
                title=f"🎉🎂 **Feliz Aniversário, {info['nome']}!** 🎂🎉",
                color=discord.Color.blurple()
            )
            embed.set_image(url=info["link_foto"])
            await canal.send(mention, embed=embed)
            await ctx.send(f"✅ Simulação de aniversário enviada para {info['nome']}.")
        else:
            await ctx.send("⚠️ Membro não encontrado ou sem foto.")
