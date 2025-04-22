import discord
from discord.ext import commands, tasks
from discord.ui import View, Modal, TextInput, Button, Select
from discord import SelectOption
from math import ceil
import asyncio
from datetime import datetime
import logging
import pwd



# ID do canal onde os LOGS de arquivos serão enviados
SEU_CANAL_ID = 1364212031875453059


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Armazenamento por servidor (guild_id)
auto_roles = {}
ticket_response_channels = {}
mention_roles = {}  # guild_id: cargo que será mencionado nos tickets
sugestao_channels = {}  # guild_id: canal para sugestões/reclamações
test_channels = {}  # guild_id: canal para mensagens de teste
mensagem_roles = {}  # guild_id: [lista de ids de cargos permitidos]
cargo_autorizado_mensagem = {}  # guild_id: [lista de role_ids]
ultimos_eventos = {}




import json
import os

import logging

# Configura o Logger
logging.basicConfig(
    level=logging.INFO,  # Nível de log: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%d/%m/%Y %H:%M:%S"
)

# Substitui o print padrão do discord.py por logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)  # Pode ajustar para DEBUG se quiser ver ainda mais detalhes



CAMINHO_PASTA = "/srv/dados"

# Inicializa o conjunto de arquivos anteriores
arquivos_anteriores = set()

async def monitorar_pasta():
    global arquivos_anteriores

    def mapear_arquivos():
        arquivos = {}
        for raiz, _, arquivos_encontrados in os.walk(CAMINHO_PASTA):
            for nome in arquivos_encontrados:
                caminho = os.path.join(raiz, nome)
                try:
                    arquivos[caminho] = os.stat(caminho).st_mtime
                except FileNotFoundError:
                    continue  # Pode ocorrer se o arquivo for deletado enquanto mapeia
        return arquivos

    try:
        arquivos_anteriores = mapear_arquivos()
    except Exception as e:
        print(f"Erro inicial ao listar arquivos: {e}")
        return

    await bot.wait_until_ready()
    canal = bot.get_channel(SEU_CANAL_ID)

    while True:
        await asyncio.sleep(5)

        try:
            arquivos_atuais = mapear_arquivos()

            # Detectar novos arquivos
            novos_arquivos = set(arquivos_atuais) - set(arquivos_anteriores)
            for arquivo in novos_arquivos:
                nome_arquivo = os.path.relpath(arquivo, CAMINHO_PASTA)
                info_evento = ultimos_eventos.pop(nome_arquivo, None)

                if info_evento:
                    mensagem = (
                        f"📄 **Usuário:** {info_evento['usuario']}\n"
                        f"🛠 **Alteração:** {info_evento['acao']} `{nome_arquivo}`\n"
                        f"🕒 **Data:** {info_evento['data']}"
                    )
                else:
                    mensagem = (
                        f"📄 **Usuário:** Desconhecido\n"
                        f"🛠 **Alteração:** Criou `{nome_arquivo}`\n"
                        f"🕒 **Data:** Desconhecida"
                    )

                if canal:
                    await canal.send(mensagem)

            # Detectar arquivos deletados
            arquivos_removidos = set(arquivos_anteriores) - set(arquivos_atuais)
            for arquivo in arquivos_removidos:
                nome_arquivo = os.path.relpath(arquivo, CAMINHO_PASTA)
                info_evento = ultimos_eventos.pop(nome_arquivo, None)

                if info_evento:
                    mensagem = (
                        f"📄 **Usuário:** {info_evento['usuario']}\n"
                        f"🛠 **Alteração:** {info_evento['acao']} `{nome_arquivo}`\n"
                        f"🕒 **Data:** {info_evento['data']}"
                    )
                else:
                    mensagem = (
                        f"📄 **Usuário:** Desconhecido\n"
                        f"🛠 **Alteração:** Deletou `{nome_arquivo}`\n"
                        f"🕒 **Data:** Desconhecida"
                    )

                if canal:
                    await canal.send(mensagem)

            # Detectar arquivos modificados
            arquivos_comuns = set(arquivos_anteriores) & set(arquivos_atuais)
            for arquivo in arquivos_comuns:
                if arquivos_anteriores[arquivo] != arquivos_atuais[arquivo]:
                    nome_arquivo = os.path.relpath(arquivo, CAMINHO_PASTA)
                    info_evento = ultimos_eventos.pop(nome_arquivo, None)

                    if info_evento:
                        mensagem = (
                            f"📄 **Usuário:** {info_evento['usuario']}\n"
                            f"🛠 **Alteração:** {info_evento['acao']} `{nome_arquivo}`\n"
                            f"🕒 **Data:** {info_evento['data']}"
                        )
                    else:
                        mensagem = (
                            f"📄 **Usuário:** Desconhecido\n"
                            f"🛠 **Alteração:** Alterou `{nome_arquivo}`\n"
                            f"🕒 **Data:** Desconhecida"
                        )

                    if canal:
                        await canal.send(mensagem)

            arquivos_anteriores = arquivos_atuais

        except Exception as e:
            print(f"Erro ao monitorar a pasta: {e}")



def traduzir_uid(uid):
    try:
        return pwd.getpwuid(int(uid)).pw_name
    except:
        return "Desconhecido"

def interpretar_syscall(linha):
    if 'SYSCALL=openat' in linha and 'O_CREAT' in linha:
        return "Criou um arquivo"
    elif 'SYSCALL=unlinkat' in linha:
        return "Deletou um arquivo"
    elif 'SYSCALL=renameat' in linha:
        return "Renomeou/moveu um arquivo"
    else:
        return None


# Carregar Tipos de Mensagem
tipos_mensagem = {}

def carregar_tipos_mensagem():
    global tipos_mensagem
    if os.path.exists("tipos_mensagem.json"):
        with open("tipos_mensagem.json", "r", encoding="utf-8") as f:
            tipos_mensagem = json.load(f)
    else:
        tipos_mensagem = {
            "aviso": {"emoji": "⚠️", "cor": "#f1c40f"},
            "informacao": {"emoji": "ℹ️", "cor": "#3498db"},
            "aviso_importante": {"emoji": "🚨", "cor": "#e74c3c"},
            "desligamento": {"emoji": "🏴", "cor": "#7f8c8d"},
            "contratacao": {"emoji": "🟢", "cor": "#2ecc71"}
        }
        salvar_tipos_mensagem()

def salvar_tipos_mensagem():
    with open("tipos_mensagem.json", "w", encoding="utf-8") as f:
        json.dump(tipos_mensagem, f, indent=4, ensure_ascii=False)





def salvar_dados():
    dados = {
        "auto_roles": auto_roles,
        "ticket_response_channels": ticket_response_channels,
        "mention_roles": mention_roles,
        "sugestao_channels": sugestao_channels,
        "test_channels": test_channels,
        "mensagem_roles": mensagem_roles,
        "cargo_autorizado_mensagem": cargo_autorizado_mensagem,
    }

    temp_file = "dados_servidor_temp.json"
    final_file = "dados_servidor.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    os.replace(temp_file, final_file)

def carregar_dados():
    if os.path.exists("dados_servidor.json"):
        with open("dados_servidor.json", "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            if conteudo:
                dados = json.loads(conteudo)
                auto_roles.update(dados.get("auto_roles", {}))
                ticket_response_channels.update(dados.get("ticket_response_channels", {}))
                mention_roles.update(dados.get("mention_roles", {}))
                sugestao_channels.update(dados.get("sugestao_channels", {}))
                test_channels.update(dados.get("test_channels", {}))
                mensagem_roles.update(dados.get("mensagem_roles", {}))  # <--- ADICIONE ESTA LINHA
                cargo_autorizado_mensagem.update(dados.get("cargo_autorizado_mensagem", {}))



@bot.event
async def on_member_join(member):
    role_id = auto_roles.get(str(member.guild.id))
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            print(f"✅ Cargo {role.name} atribuído a {member.name}")

# Comando: define o cargo automático
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
            salvar_dados()  # <<< Aqui salva IMEDIATAMENTE!
            role = ctx.guild.get_role(selected_role_id)
            await interaction.response.send_message(f"✅ Cargo automático configurado para: **{role.name}**", ephemeral=True)

    view = View()
    view.add_item(RoleSelect())
    await ctx.send("👥 Selecione o cargo automático:", view=view)


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        bot.add_view(TicketButtonView())
        bot.add_view(SugestaoView())
    except Exception as e:
        print(f"⚠️ Erro ao adicionar Views: {e}")

    try:
        bot.loop.create_task(monitorar_audit_log())  # Monitorar audit
        bot.loop.create_task(monitorar_pasta())      # Monitorar pasta
    except Exception as e:
        print(f"⚠️ Erro ao criar Tasks: {e}")




def extrair_valor(texto, campo):
    try:
        inicio = texto.index(f'{campo}=') + len(campo) + 1
        fim = texto.find(' ', inicio)
        if fim == -1:
            fim = len(texto)
        valor = texto[inicio:fim].strip('"')
        if valor == "unset":
            return "Usuário não autenticado"
        return valor
    except ValueError:
        return "Desconhecido"


def extrair_data(texto):
    try:
        inicio = texto.index('audit(') + 6
        fim = texto.index(':', inicio)
        timestamp = float(texto[inicio:fim])
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%d/%m/%Y %Hh%Mmin%Ss')
    except Exception:
        return "Data desconhecida"


async def monitorar_audit_log():
    await bot.wait_until_ready()
    path_log = '/var/log/audit/audit.log'

    with open(path_log, 'r') as f:
        f.seek(0, os.SEEK_END)
        buffer_evento = ""

        while True:
            linha = f.readline()
            if not linha:
                await asyncio.sleep(0.5)
                continue

            buffer_evento += linha

            # Continua juntando linhas até formar o evento completo
            if linha.strip() == "" or linha.startswith("type="):
                continue

            if 'pasta_dados' not in buffer_evento:
                buffer_evento = ""
                continue

            usuario_id = extrair_valor(buffer_evento, 'UID')

            # >>>>>>> este if tem que estar indentado junto
            if usuario_id in ("0", "unset", "Desconhecido"):
                usuario_id = extrair_valor(buffer_evento, 'AUID')

            usuario_nome = traduzir_uid(usuario_id)

            syscall = extrair_valor(buffer_evento, 'SYSCALL')
            arquivo = extrair_valor(buffer_evento, 'name')
            data_hora = extrair_data(buffer_evento)

            # Determina o tipo de alteração
            if syscall == 'openat' and 'O_CREAT' in buffer_evento:
                alteracao = "Criou"
            elif syscall == 'unlinkat':
                alteracao = "Deletou"
            elif syscall == 'renameat':
                alteracao = "Renomeou/Moveu"
            elif syscall == 'setxattr':
                alteracao = "Alterou"
            else:
                buffer_evento = ""
                continue  # Pula syscalls que não nos interessam

            # Armazena o evento no cache para o monitorar_pasta() usar
            ultimos_eventos[arquivo] = {
                "usuario": usuario_nome,
                "acao": alteracao,
                "data": data_hora
            }

            buffer_evento = ""  # Limpa o buffer para o próximo evento



# Comando: define o cargo a ser mencionado nos tickets
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
            super().__init__(placeholder="Selecione o cargo para mencionar nos tickets", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected = int(self.values[0])
            mention_roles[str(ctx.guild.id)] = selected
            salvar_dados()  # <<< E aqui também!
            role = ctx.guild.get_role(selected)
            await interaction.response.send_message(f"📌 Cargo a ser mencionado nos tickets definido como: **{role.mention}**", ephemeral=True)

    view = View()
    view.add_item(MentionRoleSelect())
    await ctx.send("🔣 Selecione o cargo que será mencionado nos tickets:", view=view)


# Modal que abre com o botão dos tickets
class TicketModal(Modal, title="Solicitar Cargo"):
    nome = TextInput(label="Nome", placeholder="Digite seu nome completo", style=discord.TextStyle.short)
    cargo = TextInput(label="Setor / Cargo desejado", placeholder="Ex: Financeiro, RH...", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        mod_channel_id = ticket_response_channels.get(str(interaction.guild.id))
        mod_channel = bot.get_channel(mod_channel_id)
        cargo_id = mention_roles.get(str(interaction.guild.id))

        try:
            await interaction.user.edit(nick=self.nome.value)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não consegui alterar seu apelido (permite o bot modificar nicknames?)", ephemeral=True)
            return

        if not mod_channel:
            await interaction.response.send_message("❌ Nenhum canal configurado para envio de tickets.", ephemeral=True)
            return

        embed = discord.Embed(title="📉 Novo Pedido de Cargo", color=discord.Color.blurple())
        embed.add_field(name="Usuário", value=interaction.user.mention, inline=False)
        embed.add_field(name="Cargo desejado", value=self.cargo.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        mention = f"<@&{cargo_id}>" if cargo_id else ""

        await mod_channel.send(content=mention, embed=embed)
        await interaction.response.send_message("✅ Pedido enviado com sucesso! Seu apelido foi atualizado.", ephemeral=True)

class TicketButton(Button):
    def __init__(self):
        super().__init__(label="Solicitar cargo", emoji="📬", style=discord.ButtonStyle.secondary, custom_id="ticket_button")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton())

#comando de ping

@bot.command()
async def ping(ctx):
    await ctx.send(f"🏓 Pong! Latência: `{round(bot.latency * 1000)}ms`")


# Comando: configura o canal onde os tickets serão enviados
@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    all_channels = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
    if not all_channels:
        await ctx.send("❌ Não há canais disponíveis para seleção.")
        return

    per_page = 25
    total_pages = ceil(len(all_channels) / per_page)

    class ChannelSelect(Select):
        def __init__(self, page=0):
            self.page = page
            start = page * per_page
            end = start + per_page
            options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in all_channels[start:end]]
            super().__init__(placeholder=f"Página {page + 1} de {total_pages}", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected_channel_id = int(self.values[0])
            ticket_response_channels[str(ctx.guild.id)] = selected_channel_id
            await interaction.response.send_message(f"✅ Canal de envio configurado para <#{selected_channel_id}>.", ephemeral=True)
            await ctx.send("📉 Solicite seu cargo abaixo:", view=TicketButtonView())

    class ChannelSelectionView(View):
        def __init__(self):
            super().__init__(timeout=60)
            self.page = 0
            self.select = ChannelSelect(self.page)
            self.add_item(self.select)

            if total_pages > 1:
                self.prev = Button(label="⏪ Anterior", style=discord.ButtonStyle.secondary)
                self.next = Button(label="⏩ Próximo", style=discord.ButtonStyle.secondary)
                self.prev.callback = self.go_prev
                self.next.callback = self.go_next
                self.add_item(self.prev)
                self.add_item(self.next)

        async def go_prev(self, interaction):
            if self.page > 0:
                self.page -= 1
                await self.update(interaction)

        async def go_next(self, interaction):
            if self.page < total_pages - 1:
                self.page += 1
                await self.update(interaction)

        async def update(self, interaction):
            self.clear_items()
            self.select = ChannelSelect(self.page)
            self.add_item(self.select)
            if total_pages > 1:
                self.add_item(self.prev)
                self.add_item(self.next)
            await interaction.response.edit_message(view=self)

    await ctx.send("📌 Selecione o canal para onde os tickets serão enviados:", view=ChannelSelectionView())

# Comando: define o canal para sugestões/reclamações anônimas
@bot.command()
@commands.has_permissions(administrator=True)
async def reclamacao(ctx):
    canais = [c for c in ctx.guild.text_channels if c.permissions_for(ctx.guild.me).send_messages]
    options = [SelectOption(label=c.name[:100], value=str(c.id)) for c in canais[:25]]

    class CanalSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Escolha onde as mensagens anônimas serão enviadas", options=options)

        async def callback(self, interaction):
            canal_id = int(self.values[0])
            sugestao_channels[str(ctx.guild.id)] = canal_id
            await interaction.response.send_message("✅ Canal de destino configurado!", ephemeral=True)
            await ctx.send(
                "**📜 Envie sua sugestão ou reclamação de forma anônima. Ninguém saberá que foi você.**",
                view=SugestaoView()
            )

    view = View()
    view.add_item(CanalSelect())
    await ctx.send("🔹 Escolha o canal que vai receber as sugestões/reclamações:", view=view)

class SugestaoModal(Modal, title="Envie sua sugestão ou reclamação"):
    mensagem = TextInput(label="Escreva aqui", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction):
        canal_id = sugestao_channels.get(str(interaction.guild.id))
        canal = bot.get_channel(canal_id)
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

@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx):
    class ConfirmarLimpeza(Button):
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

@bot.command()
@commands.has_permissions(administrator=True)
async def tipos(ctx):
    if not tipos_mensagem:
        await ctx.send("⚠️ Nenhum tipo de mensagem cadastrado.")
        return

    embed = discord.Embed(
        title="📚 Tipos de Mensagem Cadastrados",
        color=discord.Color.blue()
    )

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
        nome = TextInput(label="Nome do Tipo", placeholder="Ex: Alerta Importante", style=discord.TextStyle.short)
        emoji = TextInput(label="Emoji", placeholder="Ex: 🚨", style=discord.TextStyle.short)
        cor = TextInput(label="Cor Hexadecimal", placeholder="Ex: #ff0000", style=discord.TextStyle.short)

        async def on_submit(self, interaction: discord.Interaction):
            nome_formatado = self.nome.value.lower().replace(" ", "_")
            tipos_mensagem[nome_formatado] = {
                "emoji": self.emoji.value,
                "cor": self.cor.value
            }
            salvar_tipos_mensagem()
            await interaction.response.send_message(f"✅ Tipo `{self.nome.value}` criado com sucesso!", ephemeral=True)

    # Agora cria um botão para abrir o modal:
    class CriarTipoButton(Button):
        def __init__(self):
            super().__init__(label="Criar Novo Tipo", style=discord.ButtonStyle.primary)

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.send_modal(CriarTipoModal())

    view = View()
    view.add_item(CriarTipoButton())
    await ctx.send("➕ Clique abaixo para criar um novo tipo de mensagem:", view=view)


@bot.command()
@commands.has_permissions(administrator=True)
async def apagatipo(ctx):
    if not tipos_mensagem:
        await ctx.send("⚠️ Nenhum tipo de mensagem cadastrado para apagar.")
        return

    options = [
        SelectOption(label=tipo.replace('_', ' ').title(), value=tipo)
        for tipo in tipos_mensagem.keys()
    ]

    class ApagarTipoSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Selecione o tipo para apagar", options=options)

        async def callback(self, interaction):
            tipo = self.values[0]
            tipos_mensagem.pop(tipo, None)
            salvar_tipos_mensagem()
            await interaction.response.send_message(f"🗑️ Tipo `{tipo.replace('_', ' ').title()}` apagado com sucesso!", ephemeral=True)

    view = View()
    view.add_item(ApagarTipoSelect())
    await ctx.send("🗑️ Selecione o tipo de mensagem que deseja apagar:", view=view)



# Comando para definir quais cargos podem usar !mensagem
@bot.command()
@commands.has_permissions(administrator=True)
async def setcargomensagem(ctx):
    roles = [
        r for r in ctx.guild.roles
        if not r.is_bot_managed() and r.name.strip() and r.name != "@everyone"
    ]

    options = []
    for r in roles:
        nome_limpo = r.name.strip()
        if nome_limpo:
            options.append(
                SelectOption(label=nome_limpo[:100], value=str(r.id))
            )

    options = options[:25]  # Limita a 25 opções para não dar erro

    if not options:
        await ctx.send("⚠️ Nenhum cargo disponível para configurar.")
        return

    class CargoMensagemSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Selecione os cargos que poderão usar !mensagem", options=options, min_values=1, max_values=len(options))

        async def callback(self, interaction: discord.Interaction):
            guild_id = str(ctx.guild.id)
            cargo_autorizado_mensagem[guild_id] = [int(value) for value in self.values]
            salvar_dados()
            await interaction.response.send_message("✅ Cargos autorizados para usar `!mensagem` atualizados!", ephemeral=True)

    view = View(timeout=60)
    view.add_item(CargoMensagemSelect())
    await ctx.send("🔹 Selecione os cargos que poderão usar `!mensagem`:", view=view)

    # Apaga o comando depois que mandar o menu
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def mensagem(ctx):
    guild_id = str(ctx.guild.id)
    autorizado = False

    if ctx.author.guild_permissions.administrator:
        autorizado = True
    else:
        autorizados = cargo_autorizado_mensagem.get(guild_id, [])
        user_roles = [role.id for role in ctx.author.roles]
        if any(role in autorizados for role in user_roles):
            autorizado = True

    if not autorizado:
        await ctx.send("🚫 Você não tem permissão para usar o comando !mensagem.", delete_after=5)
        return

    if not tipos_mensagem:
        await ctx.send("⚠️ Nenhum tipo de mensagem cadastrado.", delete_after=5)
        return

    class TipoSelect(Select):
        def __init__(self):
            options = [
                SelectOption(label=tipo.replace('_', ' ').title(), value=tipo, emoji=info.get("emoji", "📝"))
                for tipo, info in tipos_mensagem.items()
            ]
            super().__init__(placeholder="Escolha o tipo da mensagem", options=options)

        async def callback(self, interaction_tipo: discord.Interaction):
            tipo_escolhido = self.values[0]

            try:
                await interaction_tipo.message.delete()
            except:
                pass

            class ModalMensagem(Modal, title="Criar Mensagem"):
                conteudo = TextInput(label="Mensagem", style=discord.TextStyle.paragraph, placeholder="Digite a mensagem...", required=True)
                imagem = TextInput(label="Imagem (opcional)", placeholder="URL da imagem...", required=False)

                async def on_submit(self, interaction_modal: discord.Interaction):
                    info_tipo = tipos_mensagem.get(tipo_escolhido)
                    cor = int(info_tipo.get("cor", "#3498db").replace("#", ""), 16)

                    embed = discord.Embed(
                        title=f"{info_tipo.get('emoji', '📢')} {tipo_escolhido.replace('_', ' ').title()}",
                        description=self.conteudo.value,
                        color=cor,
                        timestamp=datetime.utcnow()
                    )

                    if self.imagem.value:
                        embed.set_image(url=self.imagem.value)

                    roles = [
                        r for r in interaction_modal.guild.roles
                        if not r.is_bot_managed() and r.name.strip() and r.name != "@everyone"
                    ]

                    options_cargos = []
                    for r in roles:
                        nome_limpo = r.name.strip()
                        if nome_limpo:
                            options_cargos.append(
                                SelectOption(label=nome_limpo[:100], value=str(r.id))
                            )

                    options_cargos = options_cargos[:25]
                    options_cargos.insert(0, SelectOption(label="Não mencionar ninguém", value="none"))

                    if not options_cargos:
                        await interaction_modal.channel.send(embed=embed)
                        await interaction_modal.response.send_message("✅ Mensagem enviada sem menção!", ephemeral=True)
                        return

                    class CargoSelect(Select):
                        def __init__(self):
                            super().__init__(
                                placeholder="Escolha quem será mencionado (pode selecionar vários)",
                                options=options_cargos,
                                min_values=1,
                                max_values=len(options_cargos)
                            )

                        async def callback(self, interaction_cargo: discord.Interaction):
                            mencao_ids = self.values

                            try:
                                await interaction_cargo.message.delete()
                            except:
                                pass

                            if "none" in mencao_ids:
                                await interaction_cargo.channel.send(embed=embed)
                            else:
                                mencoes = [f"<@&{mencao_id}>" for mencao_id in mencao_ids]
                                content = " ".join(mencoes)
                                await interaction_cargo.channel.send(content=content, embed=embed)

                            await interaction_cargo.response.send_message("✅ Mensagem enviada com sucesso!", ephemeral=True)

                    view_cargo = View(timeout=60)
                    view_cargo.add_item(CargoSelect())
                    await interaction_modal.response.send_message("🔔 Escolha quem será mencionado na mensagem:", view=view_cargo, ephemeral=True)

            await interaction_tipo.response.send_modal(ModalMensagem())

    view_tipo = View(timeout=60)
    view_tipo.add_item(TipoSelect())
    await ctx.send("📚 Selecione o tipo da mensagem:", view=view_tipo)

    try:
        await ctx.message.delete()
    except:
        pass


@bot.command()
@commands.has_permissions(administrator=True)
async def removecargomensagem(ctx):
    guild_id = str(ctx.guild.id)
    cargos_autorizados = cargo_autorizado_mensagem.get(guild_id, [])

    if not cargos_autorizados:
        await ctx.send("⚠️ Nenhum cargo autorizado para remover.", delete_after=5)
        return

    # Monta lista de opções dos cargos que estão atualmente autorizados
    guild_roles = ctx.guild.roles
    options = []
    for role_id in cargos_autorizados:
        role = discord.utils.get(guild_roles, id=role_id)
        if role and role.name.strip() and role.name != "@everyone":
            nome_limpo = role.name.strip()
            options.append(
                SelectOption(label=nome_limpo[:100], value=str(role.id))
            )

    options = options[:25]  # Limita a 25 para não dar erro

    if not options:
        await ctx.send("⚠️ Nenhum cargo válido encontrado para remover.", delete_after=5)
        return

    class RemoverCargoMensagemSelect(Select):
        def __init__(self):
            super().__init__(placeholder="Selecione o cargo para remover da permissão", options=options)

        async def callback(self, interaction: discord.Interaction):
            role_id = int(self.values[0])
            if role_id in cargo_autorizado_mensagem.get(guild_id, []):
                cargo_autorizado_mensagem[guild_id].remove(role_id)
                salvar_dados()
                await interaction.response.send_message("✅ Cargo removido da lista de autorizados para `!mensagem`.", ephemeral=True)
            else:
                await interaction.response.send_message("⚠️ Cargo não encontrado na lista de autorizados.", ephemeral=True)

    view = View(timeout=60)
    view.add_item(RemoverCargoMensagemSelect())
    await ctx.send("🔹 Selecione o cargo que você deseja remover da autorização do `!mensagem`:", view=view)

    # Apaga a mensagem de comando enviada
    try:
        await ctx.message.delete()
    except:
        pass



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





@bot.event
async def on_command_completion(ctx):
    salvar_dados()

@bot.event
async def on_guild_join(guild):
    salvar_dados()

@bot.event
async def on_guild_remove(guild):
    auto_roles.pop(str(guild.id), None)
    ticket_response_channels.pop(str(guild.id), None)
    mention_roles.pop(str(guild.id), None)
    sugestao_channels.pop(str(guild.id), None)
    test_channels.pop(str(guild.id), None)
    salvar_dados()


from dotenv import load_dotenv

load_dotenv()
carregar_dados() 
carregar_tipos_mensagem()  

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

