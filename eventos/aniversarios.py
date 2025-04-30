import discord
from datetime import datetime
import asyncio
from dados.salvar import carregar_aniversarios
from config import CANAL_ANIVERSARIO_ID

async def verificar_aniversarios(bot):
    aniversarios = carregar_aniversarios()
    hoje = datetime.now().strftime("%m-%d")
    canal = bot.get_channel(CANAL_ANIVERSARIO_ID)

    for user_id, info in aniversarios.items():
        if datetime.strptime(info["data_nascimento"], "%Y-%m-%d").strftime("%m-%d") == hoje:
            guild = bot.get_guild(1359193389022707823)  # TODO: parametrizar ou mover para config
            membro = guild.get_member(int(user_id)) if guild else None
            if membro:
                link_imagem = info.get("link_foto")
                if not link_imagem:
                    print(f"⚠️ Sem imagem para {info['nome']}")
                    continue

                mention = f"{membro.mention} <@&1359579655702839458>"  # TODO: mover ID para config
                embed = discord.Embed(
                    title=f"🎉🎂 **Feliz Aniversário, {info['nome']}!** 🎂🎉",
                    description=f"🎁 Que seu dia seja repleto de alegrias e conquistas! 💐🎉\n\n🎈 **Parabéns!** 🎈",
                    color=discord.Color.blurple()
                )
                embed.set_image(url=link_imagem)
                await canal.send(mention, embed=embed)
            else:
                print(f"⚠️ Membro {info['nome']} não encontrado")

async def verificar_diariamente(bot):
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            await verificar_aniversarios(bot)
        await asyncio.sleep(60)
