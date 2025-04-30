from discord.ext import commands
from discord.ui import View, Select
from discord import SelectOption, Interaction
from dados.salvar import salvar_dados, auto_roles, mention_roles, cargo_autorizado_mensagem


def setup(bot):

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

            async def callback(self, interaction: Interaction):
                selected_id = int(self.values[0])
                auto_roles[str(ctx.guild.id)] = selected_id
                salvar_dados()
                role = ctx.guild.get_role(selected_id)
                await interaction.response.send_message(f"✅ Cargo automático definido: **{role.name}**", ephemeral=True)

        view = View()
        view.add_item(RoleSelect())
        await ctx.send("👥 Escolha o cargo automático:", view=view)


    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setcargo(ctx):
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
        options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25] if r.name.strip()]

        if not options:
            await ctx.send("⚠️ Nenhum cargo válido encontrado.")
            return

        class MentionRoleSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Cargo a mencionar nos tickets", options=options)

            async def callback(self, interaction: Interaction):
                selected = int(self.values[0])
                mention_roles[str(ctx.guild.id)] = selected
                salvar_dados()
                role = ctx.guild.get_role(selected)
                await interaction.response.send_message(f"📌 Cargo a ser mencionado: **{role.mention}**", ephemeral=True)

        view = View()
        view.add_item(MentionRoleSelect())
        await ctx.send("🔣 Escolha o cargo para menção nos tickets:", view=view)


    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setcargomensagem(ctx):
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
        options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25] if r.name.strip()]

        if not options:
            await ctx.send("⚠️ Nenhum cargo disponível para configurar.")
            return

        class CargoMensagemSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Cargos autorizados para !mensagem", options=options, min_values=1, max_values=len(options))

            async def callback(self, interaction: Interaction):
                ids = [int(value) for value in self.values]
                cargo_autorizado_mensagem[str(ctx.guild.id)] = ids
                salvar_dados()
                await interaction.response.send_message("✅ Cargos autorizados atualizados!", ephemeral=True)

        view = View(timeout=60)
        view.add_item(CargoMensagemSelect())
        await ctx.send("🔹 Escolha os cargos autorizados para `!mensagem`:", view=view)


    @bot.command()
    @commands.has_permissions(administrator=True)
    async def removecargomensagem(ctx):
        guild_id = str(ctx.guild.id)
        cargos = cargo_autorizado_mensagem.get(guild_id, [])
        roles = [ctx.guild.get_role(rid) for rid in cargos if ctx.guild.get_role(rid)]
        options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25] if r.name.strip()]

        if not options:
            await ctx.send("⚠️ Nenhum cargo autorizado para remover.")
            return

        class RemoverCargoSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Remover cargo autorizado", options=options)

            async def callback(self, interaction: Interaction):
                role_id = int(self.values[0])
                cargo_autorizado_mensagem[guild_id].remove(role_id)
                salvar_dados()
                await interaction.response.send_message("✅ Cargo removido da autorização de `!mensagem`.", ephemeral=True)

        view = View(timeout=60)
        view.add_item(RemoverCargoSelect())
        await ctx.send("🔹 Escolha o cargo a remover da autorização:", view=view)
