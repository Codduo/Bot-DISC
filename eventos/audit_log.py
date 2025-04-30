import asyncio
import pwd
from datetime import datetime

ultimos_eventos = {}

async def monitorar_audit_log(bot):
    await bot.wait_until_ready()
    path_log = '/var/log/audit/audit.log'

    try:
        with open(path_log, 'r') as f:
            f.seek(0, 2)
            evento_atual = ""
            ultimo_id = None

            while True:
                linha = f.readline()
                if not linha:
                    await asyncio.sleep(0.5)
                    continue

                if 'type=SYSCALL' in linha:
                    try:
                        inicio = linha.index('audit(') + 6
                        fim = linha.index(':', inicio)
                        audit_id = linha[inicio:fim]
                    except:
                        audit_id = None

                    if audit_id != ultimo_id and evento_atual:
                        await interpretar_evento(evento_atual)
                        evento_atual = ""

                    ultimo_id = audit_id

                evento_atual += linha
    except Exception as e:
        print(f"Erro ao monitorar audit.log: {e}")

async def interpretar_evento(evento):
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
        acao = "Criou"
    elif syscall == 'unlinkat':
        acao = "Deletou"
    elif syscall == 'renameat':
        acao = "Renomeou/Moveu"
    elif syscall == 'setxattr':
        acao = "Alterou"
    else:
        return

    ultimos_eventos[arquivo] = {
        "usuario": usuario_nome,
        "acao": acao,
        "data": data_hora
    }

def traduzir_uid(uid):
    try:
        return pwd.getpwuid(int(uid)).pw_name
    except:
        return "Desconhecido"

def extrair_valor(texto, campo):
    try:
        inicio = texto.index(f'{campo}=') + len(campo) + 1
        fim = texto.find(' ', inicio)
        if fim == -1:
            fim = len(texto)
        valor = texto[inicio:fim].strip('"')
        return "Usuário não autenticado" if valor == "unset" else valor
    except ValueError:
        return "Desconhecido"

def extrair_data(texto):
    try:
        inicio = texto.index('audit(') + 6
        fim = texto.index(':', inicio)
        timestamp = float(texto[inicio:fim])
        return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %Hh%Mmin%Ss')
    except:
        return "Data desconhecida"
