import os
import json

# Estruturas globais por servidor
auto_roles = {}
ticket_response_channels = {}
mention_roles = {}
sugestao_channels = {}
test_channels = {}
mensagem_roles = {}
cargo_autorizado_mensagem = {}
tipos_mensagem = {}


# Arquivos de dados
ARQUIVO_DADOS = "dados_servidor.json"
ARQUIVO_TIPOS = "tipos_mensagem.json"


def salvar_dados():
    dados = {
        "auto_roles": auto_roles,
        "ticket_response_channels": ticket_response_channels,
        "mention_roles": mention_roles,
        "sugestao_channels": sugestao_channels,
        "test_channels": test_channels,
        "mensagem_roles": mensagem_roles,
        "cargo_autorizado_mensagem": cargo_autorizado_mensagem
    }
    temp = "dados_servidor_temp.json"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)
    os.replace(temp, ARQUIVO_DADOS)


def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            if conteudo:
                dados = json.loads(conteudo)
                auto_roles.update(dados.get("auto_roles", {}))
                ticket_response_channels.update(dados.get("ticket_response_channels", {}))
                mention_roles.update(dados.get("mention_roles", {}))
                sugestao_channels.update(dados.get("sugestao_channels", {}))
                test_channels.update(dados.get("test_channels", {}))
                mensagem_roles.update(dados.get("mensagem_roles", {}))
                cargo_autorizado_mensagem.update(dados.get("cargo_autorizado_mensagem", {}))


def remover_guild(guild_id):
    gid = str(guild_id)
    auto_roles.pop(gid, None)
    ticket_response_channels.pop(gid, None)
    mention_roles.pop(gid, None)
    sugestao_channels.pop(gid, None)
    test_channels.pop(gid, None)
    mensagem_roles.pop(gid, None)
    cargo_autorizado_mensagem.pop(gid, None)
    salvar_dados()


def carregar_tipos_mensagem():
    global tipos_mensagem
    if os.path.exists(ARQUIVO_TIPOS):
        with open(ARQUIVO_TIPOS, "r", encoding="utf-8") as f:
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
    with open(ARQUIVO_TIPOS, "w", encoding="utf-8") as f:
        json.dump(tipos_mensagem, f, indent=4, ensure_ascii=False)


def carregar_aniversarios():
    if os.path.exists("aniversarios.json"):
        with open("aniversarios.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_aniversarios(aniversarios):
    with open("aniversarios.json", "w", encoding="utf-8") as f:
        json.dump(aniversarios, f, indent=4, ensure_ascii=False)
