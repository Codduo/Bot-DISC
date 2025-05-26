import json
import os

# ===== DATA STORAGE =====
auto_roles = {}
ticket_response_channels = {}
mention_roles = {}
sugestao_channels = {}
ticket_categories = {}
ticket_support_roles = {}

# ===== CONFIGURAÇÕES DOS TIPOS DE SUPORTE =====
SUPPORT_TYPES = {
    "tecnico": {
        "name": "Suporte Técnico",
        "emoji": "🖥️",
        "role_id": 1359194954756264120,
        "description": "Para problemas técnicos e TI"
    },
    "kommo": {
        "name": "Suporte Kommo",
        "emoji": "📱",
        "role_id": 1373012855271719003,
        "description": "Para questões do sistema Kommo"
    },
    "rh": {
        "name": "Suporte RH",
        "emoji": "👥",
        "role_id": 1359505353653489694,
        "description": "Para questões de Recursos Humanos"
    },
    "gerencia": {
        "name": "Suporte Gerência",
        "emoji": "💼",
        "role_id": 1359504498048893070,
        "description": "Para questões gerenciais"
    }
}

# ===== DATA MANAGEMENT =====
def salvar_dados():
    """Salva todos os dados do bot em arquivo JSON."""
    dados = {
        "auto_roles": auto_roles,
        "ticket_response_channels": ticket_response_channels,
        "mention_roles": mention_roles,
        "sugestao_channels": sugestao_channels,
        "ticket_categories": ticket_categories,
        "ticket_support_roles": ticket_support_roles,
    }
    
    try:
        with open("dados_servidor.json", "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Erro ao salvar dados: {e}")

def carregar_dados():
    """Carrega todos os dados do bot do arquivo JSON."""
    global auto_roles, ticket_response_channels, mention_roles
    global sugestao_channels, ticket_categories, ticket_support_roles
    
    try:
        if os.path.exists("dados_servidor.json"):
            with open("dados_servidor.json", "r", encoding="utf-8") as f:
                dados = json.load(f)
                auto_roles.update(dados.get("auto_roles", {}))
                ticket_response_channels.update(dados.get("ticket_response_channels", {}))
                mention_roles.update(dados.get("mention_roles", {}))
                sugestao_channels.update(dados.get("sugestao_channels", {}))
                ticket_categories.update(dados.get("ticket_categories", {}))
                ticket_support_roles.update(dados.get("ticket_support_roles", {}))
                print("✅ Dados carregados com sucesso")
    except Exception as e:
        print(f"⚠️ Erro ao carregar dados: {e}")

def get_support_type_info(support_type):
    """Retorna informações de um tipo de suporte específico."""
    return SUPPORT_TYPES.get(support_type, None)

def get_all_support_types():
    """Retorna todos os tipos de suporte disponíveis."""
    return SUPPORT_TYPES

def cleanup_guild_data(guild_id):
    """Remove dados de um servidor específico."""
    guild_id = str(guild_id)
    auto_roles.pop(guild_id, None)
    ticket_response_channels.pop(guild_id, None)
    mention_roles.pop(guild_id, None)
    sugestao_channels.pop(guild_id, None)
    ticket_categories.pop(guild_id, None)
    ticket_support_roles.pop(guild_id, None)