import discord
from discord.ext import commands
from discord.ui import View, Select
from discord import SelectOption

auto_roles = {}
mention_roles = {}
mensagem_roles = {}
cargo_autorizado_mensagem = {}

def carregar_dados_servidor():
    import json, os
    if os.path.exists("dados_servidor.json"):
        with open("dados_servidor.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
            auto_roles.update(dados.get("auto_roles", {}))
            mention_roles.update(dados.get("mention_roles", {}))
            mensagem_roles.update(dados.get("mensagem_roles", {}))
            cargo_autorizado_mensagem.update(dados.get("cargo_autorizado_mensagem", {}))

def salvar_dados_servidor():
    import json
    dados = {
        "auto_roles": auto_roles,
        "mention_roles": mention_roles,
        "mensagem_roles": mensagem_roles,
        "cargo_autorizado_mensagem": cargo_autorizado_mensagem,
    }
    with open("dados_servidor.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def setup_cargos_commands(bot):

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
        options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]

        class RoleSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Selecione o cargo automático", options=options)

            async def callback(self, interaction):
                selected = int(self.values[0])
                auto_roles[str(ctx.guild.id)] = selected
                salvar_dados_servidor()
                role = ctx.guild.get_role(selected)
                await interaction.response.send_message(f"✅ Cargo automático: **{role.name}**", ephemeral=True)

        view = View()
        view.add_item(RoleSelect())
        await ctx.send("👥 Selecione o cargo automático:", view=view)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setcargo(ctx):
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
        options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]

        class MentionSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Cargo a ser mencionado nos tickets", options=options)

            async def callback(self, interaction):
                selected = int(self.values[0])
                mention_roles[str(ctx.guild.id)] = selected
                salvar_dados_servidor()
                role = ctx.guild.get_role(selected)
                await interaction.response.send_message(f"📌 Cargo mencionado: **{role.name}**", ephemeral=True)

        view = View()
        view.add_item(MentionSelect())
        await ctx.send("🔹 Selecione o cargo mencionado nos tickets:", view=view)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setcargomensagem(ctx):
        roles = [r for r in ctx.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
        options = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]

        class PermissaoSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Cargos com permissão para usar !mensagem", options=options, min_values=1, max_values=len(options))

            async def callback(self, interaction):
                guild_id = str(ctx.guild.id)
                cargo_autorizado_mensagem[guild_id] = [int(v) for v in self.values]
                salvar_dados_servidor()
                await interaction.response.send_message("✅ Permissões atualizadas!", ephemeral=True)

        view = View()
        view.add_item(PermissaoSelect())
        await ctx.send("🔐 Selecione os cargos que podem usar `!mensagem`:", view=view)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def removecargomensagem(ctx):
        guild_id = str(ctx.guild.id)
        cargos = cargo_autorizado_mensagem.get(guild_id, [])
        if not cargos:
            await ctx.send("⚠️ Nenhum cargo autorizado encontrado.")
            return

        options = []
        for role_id in cargos:
            role = discord.utils.get(ctx.guild.roles, id=role_id)
            if role:
                options.append(SelectOption(label=role.name[:100], value=str(role.id)))

        class RemoverSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Selecione o cargo para remover", options=options)

            async def callback(self, interaction):
                cargo_autorizado_mensagem[guild_id].remove(int(self.values[0]))
                salvar_dados_servidor()
                await interaction.response.send_message("🗑️ Cargo removido da permissão.", ephemeral=True)

        view = View()
        view.add_item(RemoverSelect())
        await ctx.send("🔻 Selecione o cargo a ser removido das permissões:", view=view)
