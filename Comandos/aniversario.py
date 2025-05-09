import discord
from discord.ext import commands
from discord import TextStyle
from discord.ui import Modal, TextInput
from datetime import datetime
import json
import os
import asyncio

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
            if membro:
                link_imagem = info.get("link_foto", None)
                
                if not link_imagem:
                    print(f"⚠️ Não há link de foto para o aniversariante {info['nome']}.")
                    continue
                
                mention = f"{membro.mention} <@&1359579655702839458>"
                
                embed = discord.Embed(
                    title=f"🎉🎂 **Feliz Aniversário, {info['nome']}!** 🎂🎉",
                    description=f"🎁 Que seu dia seja repleto de alegrias e conquistas! 💐🎉\n\n🎈 **Parabéns!** 🎈",
                    color=discord.Color.blurple()
                )
                embed.set_image(url=link_imagem)
                await canal.send(mention, embed=embed)
            else:
                print(f"⚠️ Membro {info['nome']} não encontrado no servidor.")

async def verificar_diariamente(bot):
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            await verificar_aniversarios(bot)
        await asyncio.sleep(60)

class AniversarioCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def adicionar_aniversario(self, ctx):
        """Adiciona um aniversariante à lista via pop-up."""
        
        class AdicionarAniversarioModal(Modal, title="Adicionar Aniversariante"):
            user_id = TextInput(label="ID do Usuário", placeholder="Ex: 1234567890", style=TextStyle.short)
            nome = TextInput(label="Nome", placeholder="Ex: João Silva", style=TextStyle.short)
            data_nascimento = TextInput(label="Data de Nascimento (YYYY-MM-DD)", placeholder="Ex: 2000-03-01", style=TextStyle.short)
            link_foto = TextInput(label="Link da Foto (Google Drive)", placeholder="Ex: https://drive.google.com/...", style=TextStyle.short)
            
            async def on_submit(self, interaction: discord.Interaction):
                user_id = self.user_id.value.strip()
                nome = self.nome.value.strip()
                data_nascimento = self.data_nascimento.value.strip()
                link_foto = self.link_foto.value.strip()
                
                if not user_id or not nome or not data_nascimento or not link_foto:
                    await interaction.response.send_message("⚠️ Todos os campos são obrigatórios.", ephemeral=True)
                    return

                try:
                    datetime.strptime(data_nascimento, "%Y-%m-%d")
                except ValueError:
                    await interaction.response.send_message("⚠️ A data deve estar no formato **YYYY-MM-DD**.", ephemeral=True)
                    return
                
                aniversarios = carregar_aniversarios()
                aniversarios[user_id] = {
                    "nome": nome,
                    "data_nascimento": data_nascimento,
                    "link_foto": link_foto
                }
                salvar_aniversarios(aniversarios)

                await interaction.response.send_message(f"✅ O aniversariante {nome} foi adicionado com sucesso!", ephemeral=True)
        
        await ctx.send("📅 Preencha as informações do aniversariante:", view=Modal())

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def simular_aniversario(self, ctx, user_id: int):
        """Simula o envio de uma imagem de aniversário com link de foto."""
        
        aniversarios = carregar_aniversarios()

        if str(user_id) not in aniversarios:
            await ctx.send(f"⚠️ O usuário com ID {user_id} não está na lista de aniversariantes.")
            return
        
        info = aniversarios[str(user_id)]
        canal = self.bot.get_channel(CANAL_ANIVERSARIO_ID)
        link_imagem = info.get("link_foto", None)
        
        if not link_imagem:
            await ctx.send("⚠️ Não há link de foto associado a este aniversariante.")
            return
        
        membro = self.bot.get_guild(1359193389022707823).get_member(int(user_id))
        if membro:
            mention = f"{membro.mention} <@&1359579655702839458>"
            
            embed = discord.Embed(
                title=f"🎉🎂 **Feliz Aniversário, {info['nome']}!** 🎂🎉",
                description="",
                color=discord.Color.blurple()
            )
            embed.set_image(url=link_imagem)
            await canal.send(mention, embed=embed)
            await ctx.send(f"✅ A mensagem de aniversário com imagem para {info['nome']} foi simulada com sucesso!")
        else:
            await ctx.send(f"⚠️ Não foi possível encontrar o membro com ID {user_id}.")

def setup(bot):
    bot.add_cog(AniversarioCommands(bot))