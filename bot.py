import asyncio
import atexit
import discord
import json
import logging
import os
import pwd
import sys
from datetime import datetime
from discord import SelectOption, TextStyle
from discord.ext import commands, tasks
from discord.ui import View, Modal, TextInput, Button, Select
from dotenv import load_dotenv
from math import ceil

#Variaveis
CANAL_ANIVERSARIO_ID = 1362040456279621892
SEU_CANAL_ID = 1364212031875453059
CAMINHO_PASTA = "/srv/dados"
TEMPO_ESPERA_CONFIRMACAO = 15  # segundos
LOCKFILE = "/tmp/bot_bmz.lock"

auto_roles = {}
ticket_response_channels = {}
mention_roles = {}
sugestao_channels = {}
test_channels = {}
mensagem_roles = {}
cargo_autorizado_mensagem = {}
ultimos_eventos = {}
tipos_mensagem = {}

arquivos_anteriores = set()
aniversarios = {} 

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

#def's
def carregar_aniversarios():
    if os.path.exists("aniversarios.json"):
        with open("aniversarios.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_aniversarios(aniversarios):
    with open("aniversarios.json", "w", encoding="utf-8") as f:
        json.dump(aniversarios, f, indent=4, ensure_ascii=False)

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

def remove_lockfile():
    if os.path.exists(LOCKFILE):
        os.remove(LOCKFILE)

#asyc def
async def verificar_aniversarios():
    aniversarios = carregar_aniversarios()  # Carrega o arquivo JSON
    hoje = datetime.now().strftime("%m-%d")  # Formato "MM-DD"
    
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

async def verificar_diariamente():
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute == 0:
            await verificar_aniversarios()
        await asyncio.sleep(60)

async def confirmar_estabilidade(arquivo):
    try:
        mod_time_inicial = os.stat(arquivo).st_mtime
    except FileNotFoundError:
        return False

    await asyncio.sleep(TEMPO_ESPERA_CONFIRMACAO)

    try:
        mod_time_final = os.stat(arquivo).st_mtime
    except FileNotFoundError:
        return False

    return mod_time_inicial == mod_time_final

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
                    continue
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

                if canal and await confirmar_estabilidade(arquivo):
                    await canal.send(mensagem)

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

async def interpretar_evento(evento: str):
    if 'pasta_dados' not in evento:
        return

    usuario_id = extrair_valor(evento, 'UID')
    if usuario_id in ("0", "unset", "Desconhecido"):
        usuario_id = extrair_valor(evento, 'AUID')

    usuario_nome = traduzir_uid(usuario_id)
    syscall = extrair_valor(evento, 'SYSCALL')
    arquivo = extrair_valor(evento, 'name')
    data_hora = extrair_data(evento)

    if not arquivo or arquivo == 'unknown':
        return

    if syscall == 'openat' and 'O_CREAT' in evento:
        alteracao = "Criou"
    elif syscall == 'unlinkat':
        alteracao = "Deletou"
    elif syscall == 'renameat':
        alteracao = "Renomeou/Moveu"
    elif syscall == 'setxattr':
        alteracao = "Alterou"
    else:
        return

    ultimos_eventos[arquivo] = {
        "usuario": usuario_nome,
        "acao": alteracao,
        "data": data_hora
    }

async def monitorar_audit_log():
    await bot.wait_until_ready()
    path_log = '/var/log/audit/audit.log'

    with open(path_log, 'r') as f:
        f.seek(0, os.SEEK_END)
        evento_atual = ""
        ultimo_audit_id = None

        while True:
            linha = f.readline()
            if not linha:
                await asyncio.sleep(0.5)
                continue

            if 'type=SYSCALL' in linha:
                try:
                    audit_inicio = linha.index('audit(') + 6
                    audit_fim = linha.index(':', audit_inicio)
                    audit_id = linha[audit_inicio:audit_fim]
                except:
                    audit_id = None

                if audit_id != ultimo_audit_id and evento_atual:
                    await interpretar_evento(evento_atual)
                    evento_atual = ""

                ultimo_audit_id = audit_id

            evento_atual += linha

#Classes 
class RoleSelect(Select):
    def __init__(self):
        super().__init__(placeholder="Selecione o cargo automático", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.values[0])
        auto_roles[str(ctx.guild.id)] = selected_role_id
        salvar_dados()
        role = ctx.guild.get_role(selected_role_id)
        await interaction.response.send_message(f"✅ Cargo automático configurado para: **{role.name}**", ephemeral=True)

class TicketModal(Modal, title="Solicitar Cargo"):
    nome = TextInput(label="Nome", placeholder="Digite seu nome completo", style=TextStyle.short)
    cargo = TextInput(label="Setor / Cargo desejado", placeholder="Ex: Financeiro, RH...", style=TextStyle.paragraph)

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

class SugestaoModal(Modal, title="Envie sua sugestão ou reclamação"):
    mensagem = TextInput(label="Escreva aqui", style=TextStyle.paragraph)

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

#BotEvent
@bot.event
async def on_member_join(member):
    role_id = auto_roles.get(str(member.guild.id))
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            print(f"✅ Cargo {role.name} atribuído a {member.name}")

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        bot.add_view(TicketButtonView())
        bot.add_view(SugestaoView())
        bot.loop.create_task(verificar_diariamente())
    except Exception as e:
        print(f"⚠️ Erro ao adicionar Views: {e}")

    try:
        bot.loop.create_task(monitorar_audit_log())
        bot.loop.create_task(monitorar_pasta())
    except Exception as e:
        print(f"⚠️ Erro ao criar Tasks: {e}")

@bot.event
async def on_guild_join(guild):
    salvar_dados()

@bot.event
async def on_command_completion(ctx):
    salvar_dados()

@bot.event
async def on_guild_remove(guild):
        auto_roles.pop(str(guild.id), None)
        ticket_response_channels.pop(str(guild.id), None)
        mention_roles.pop(str(guild.id), None)
        sugestao_channels.pop(str(guild.id), None)
        test_channels.pop(str(guild.id), None)
        salvar_dados()

load_dotenv()
carregar_dados() 
carregar_tipos_mensagem()  

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)

