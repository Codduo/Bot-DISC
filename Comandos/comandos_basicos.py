import discord
from discord.ext import commands
from discord.ui import View, Select
from discord import SelectOption
import asyncio
from math import ceil

def setup(bot, dados_globais):
    auto_roles = dados_globais["auto_roles"]
    
    @bot.event
    async def on_member_join(member):
        role_id = auto_roles.get(str(member.guild.id))
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                await member.add_roles(role)
                print(f"✅ Cargo {role.name} atribuído a {member.name}")

    @bot.command(aliases=["cargos"])
    @commands.has_permissions(administrator=True)
    async def cargo(ctx):
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
        options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25] if r.name.strip()]

        if not options:
            await ctx.send("⚠️ Nenhum cargo válido encontrado.")
            return

        class RoleSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Selecione o cargo automático", options=options)

            async def callback(self, interaction: discord.Interaction):
                selected_role_id = int(self.values[0])
                auto_roles[str(ctx.guild.id)] = selected_role_id
                role = ctx.guild.get_role(selected_role_id)
                await interaction.response.send_message(f"✅ Cargo automático configurado para: **{role.name}**", ephemeral=True)

        view = View()
        view.add_item(RoleSelect())
        await ctx.send("👥 Selecione o cargo automático:", view=view)

    @bot.command()
    async def ping(ctx):
        await ctx.send(f"🏓 Pong! Latência: `{round(bot.latency * 1000)}ms`")

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def clear(ctx):
        class ConfirmarLimpeza(discord.ui.Button):
            def __init__(self):
                super().__init__(label="Sim, limpar!", style=discord.ButtonStyle.danger)

            async def callback(self, interaction: discord.Interaction):
                if interaction.user != ctx.author:
                    await interaction.response.send_message("❌ Apenas o autor do comando pode confirmar.", ephemeral=True)
                    return

                for i in range(5, 0, -1):
                    await mensagem.edit(content=f"🧹 Limpando em {i} segundos...")
                    await asyncio.sleep(1)

                await ctx.channel.purge()
                aviso = await ctx.send("✅ Todas as mensagens foram limpas com sucesso!")
                await asyncio.sleep(3)
                await aviso.delete()

        view = View()
        view.add_item(ConfirmarLimpeza())
        mensagem = await ctx.send("⚠️ Tem certeza que deseja limpar todas as mensagens deste canal?", view=view)

    @bot.command(name="ajuda")
    async def ajuda(ctx):
        embed = discord.Embed(
            title="📖 Comandos disponíveis",
            color=discord.Color.green(),
            description="Veja abaixo os comandos que você pode usar:"
        )
        embed.add_field(name="!cargo", value="Define o cargo automático para novos membros.", inline=False)
        embed.add_field(name="!ticket", value="Escolhe o canal para os pedidos de cargo e exibe o botão.", inline=False)
        embed.add_field(name="!setcargo", value="Define qual cargo será mencionado nas mensagens do ticket.", inline=False)
        embed.add_field(name="!reclamacao", value="Cria botão para sugestões/reclamações anônimas.", inline=False)
        embed.add_field(name="!setcargomensagem", value="Define quais cargos poderão utilizar o !mensagem", inline=False)
        embed.add_field(name="!removecargomensagem", value="Remove um cargo que pode utilizar o !mensagem", inline=False)
        embed.add_field(name="!mensagem", value="Envia uma mensagem personalizada escolhendo o tipo, imagem e menção.", inline=False)
        embed.add_field(name="!tipos", value="Lista todos os tipos de mensagem cadastrados.", inline=False)
        embed.add_field(name="!criartipo", value="Cria um novo tipo de mensagem para o !mensagem.", inline=False)
        embed.add_field(name="!apagatipo", value="Apaga um tipo de mensagem cadastrado.", inline=False)
        embed.add_field(name="!ajuda", value="Mostra esta lista de comandos disponíveis.", inline=False)
        embed.add_field(name="!ping", value="Verifica se o bot está funcional e mostra o ping.", inline=False)

        await ctx.send(embed=embed)