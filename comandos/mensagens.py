from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput, Button
from discord import TextStyle, Embed, SelectOption, Interaction, Color
from dados.salvar import tipos_mensagem, salvar_tipos_mensagem, mensagem_roles, cargo_autorizado_mensagem
from datetime import datetime


def setup(bot):

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def tipos(ctx):
        if not tipos_mensagem:
            await ctx.send("⚠️ Nenhum tipo cadastrado.")
            return

        embed = Embed(title="📚 Tipos de Mensagem", color=Color.blue())
        for tipo, info in tipos_mensagem.items():
            embed.add_field(
                name=f"{info.get('emoji', '📝')} {tipo.replace('_', ' ').title()}",
                value=f"**Cor:** {info.get('cor', '#3498db')}",
                inline=False
            )
        await ctx.send(embed=embed)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def criartipo(ctx):
        class CriarTipoModal(Modal, title="Criar Novo Tipo de Mensagem"):
            nome = TextInput(label="Nome do Tipo", style=TextStyle.short)
            emoji = TextInput(label="Emoji", style=TextStyle.short)
            cor = TextInput(label="Cor Hexadecimal", placeholder="#ff0000", style=TextStyle.short)

            async def on_submit(self, interaction):
                chave = self.nome.value.lower().replace(" ", "_")
                tipos_mensagem[chave] = {
                    "emoji": self.emoji.value,
                    "cor": self.cor.value
                }
                salvar_tipos_mensagem()
                await interaction.response.send_message(f"✅ Tipo `{self.nome.value}` criado!", ephemeral=True)

        class CriarTipoButton(Button):
            def __init__(self):
                super().__init__(label="Criar Novo Tipo", style=Button.style.primary)

            async def callback(self, interaction):
                await interaction.response.send_modal(CriarTipoModal())

        view = View()
        view.add_item(CriarTipoButton())
        await ctx.send("➕ Clique para criar novo tipo:", view=view)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def apagatipo(ctx):
        if not tipos_mensagem:
            await ctx.send("⚠️ Nenhum tipo disponível para apagar.")
            return

        options = [SelectOption(label=tipo.replace('_', ' ').title(), value=tipo) for tipo in tipos_mensagem.keys()]

        class ApagarTipoSelect(Select):
            def __init__(self):
                super().__init__(placeholder="Escolha o tipo para apagar", options=options)

            async def callback(self, interaction):
                tipo = self.values[0]
                tipos_mensagem.pop(tipo, None)
                salvar_tipos_mensagem()
                await interaction.response.send_message(f"🗑️ Tipo `{tipo}` apagado com sucesso!", ephemeral=True)

        view = View()
        view.add_item(ApagarTipoSelect())
        await ctx.send("🗑️ Selecione o tipo de mensagem para apagar:", view=view)

    @bot.command()
    async def mensagem(ctx):
        guild_id = str(ctx.guild.id)
        autorizado = ctx.author.guild_permissions.administrator or any(
            r.id in cargo_autorizado_mensagem.get(guild_id, []) for r in ctx.author.roles
        )

        if not autorizado:
            await ctx.send("🚫 Você não tem permissão para usar este comando.", delete_after=5)
            return

        if not tipos_mensagem:
            await ctx.send("⚠️ Nenhum tipo cadastrado.", delete_after=5)
            return

        class TipoSelect(Select):
            def __init__(self):
                options = [
                    SelectOption(label=tipo.replace('_', ' ').title(), value=tipo, emoji=info.get("emoji", "📝"))
                    for tipo, info in tipos_mensagem.items()
                ]
                super().__init__(placeholder="Escolha o tipo da mensagem", options=options)

            async def callback(self, interaction_tipo):
                tipo_escolhido = self.values[0]

                class ModalMensagem(Modal, title="Criar Mensagem"):
                    conteudo = TextInput(label="Mensagem", style=TextStyle.paragraph, required=True)
                    imagem = TextInput(label="Imagem (opcional)", placeholder="URL da imagem", required=False)

                    async def on_submit(self, interaction_modal):
                        info = tipos_mensagem[tipo_escolhido]
                        cor = int(info.get("cor", "#3498db").replace("#", ""), 16)
                        embed = Embed(
                            title=f"{info.get('emoji', '📢')} {tipo_escolhido.replace('_', ' ').title()}",
                            description=self.conteudo.value,
                            color=cor,
                            timestamp=datetime.utcnow()
                        )
                        if self.imagem.value:
                            embed.set_image(url=self.imagem.value)

                        roles = [r for r in interaction_modal.guild.roles if not r.is_bot_managed() and r.name != "@everyone"]
                        opcoes = [SelectOption(label=r.name[:100], value=str(r.id)) for r in roles[:25]]
                        opcoes.insert(0, SelectOption(label="Não mencionar ninguém", value="none"))

                        class CargoSelect(Select):
                            def __init__(self):
                                super().__init__(placeholder="Quem será mencionado?", options=opcoes, min_values=1, max_values=len(opcoes))

                            async def callback(self, interaction_cargo):
                                mencao_ids = self.values
                                try:
                                    await interaction_cargo.message.delete()
                                except:
                                    pass
                                if "none" in mencao_ids:
                                    await interaction_cargo.channel.send(embed=embed)
                                else:
                                    mencoes = " ".join([f"<@&{mid}>" for mid in mencao_ids])
                                    await interaction_cargo.channel.send(content=mencoes, embed=embed)
                                await interaction_cargo.response.send_message("✅ Mensagem enviada!", ephemeral=True)

                        view_cargo = View(timeout=60)
                        view_cargo.add_item(CargoSelect())
                        await interaction_modal.response.send_message("🔔 Escolha quem será mencionado:", view=view_cargo, ephemeral=True)

                await interaction_tipo.response.send_modal(ModalMensagem())

        view_tipo = View(timeout=60)
        view_tipo.add_item(TipoSelect())
        await ctx.send("📚 Selecione o tipo da mensagem:", view=view_tipo)
        try:
            await ctx.message.delete()
        except:
            pass
