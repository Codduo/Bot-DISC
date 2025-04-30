# 🤖 Bot Discord Modularizado

Este projeto é um bot Discord construído com `discord.py`, agora totalmente modularizado por responsabilidades, facilitando manutenção, escalabilidade e legibilidade.

---

## 📁 Estrutura de Pastas

```
meu_bot/
│
├── bot.py                   # Entrada principal do bot
├── config.py                # Constantes globais (IDs, paths, etc.)
├── lockfile.py              # Controle de instância única
│
├── eventos/                 # Tarefas automáticas de background
│   ├── aniversarios.py      # Checagem diária de aniversários
│   ├── pasta.py             # Monitoramento de arquivos em diretório
│   └── audit_log.py         # Monitoramento do audit.log do sistema
│
├── comandos/                # Comandos do bot
│   ├── aniversarios.py      # Comandos de aniversário (!simular, !adicionar)
│   ├── cargos.py            # Configuração de cargos (!cargo, !setcargo...)
│   ├── mensagens.py         # Sistema de mensagens embed (!mensagem, !criartipo...)
│   └── sugestoes.py         # Canal de sugestões anônimas (!reclamacao)
│
├── modelos/                 # Componentes de UI do Discord
│   ├── sugestao.py          # View e Modal de sugestões anônimas
│   └── ticket.py            # Modal e botão de solicitação de cargo
│
├── dados/                   # Gerenciamento de dados persistentes
│   └── salvar.py            # Salva/carrega dados do servidor e aniversários
│
├── .env                     # Contém o token do bot (DISCORD_TOKEN)
└── requirements.txt         # Dependências (discord.py, python-dotenv, etc.)
```

---

## ▶️ Como Rodar o Bot

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Crie um arquivo `.env` com o token:
```
DISCORD_TOKEN=seu_token_aqui
```

3. Execute o bot:
```bash
python bot.py
```

---

## ✨ Como Adicionar um Novo Comando

1. Crie um novo arquivo em `comandos/`, ex: `comandos/tempo.py`
2. Siga este padrão:
```python
from discord.ext import commands

def setup(bot):
    @bot.command()
    async def tempo(ctx):
        await ctx.send("Tempo online: 5h")
```
3. Em `bot.py`, adicione:
```python
bot.load_extension("comandos.tempo")
```

---

## 🔐 Lockfile
Garante que apenas uma instância do bot esteja rodando ao mesmo tempo, via `lockfile.py` e `config.LOCKFILE`.

---

## 🗂️ Dados Persistentes
Armazenados como arquivos `.json` na raiz do projeto:
- `dados_servidor.json`
- `tipos_mensagem.json`
- `aniversarios.json`

---

## 📌 Requisitos
- Python 3.8+
- Permissões adequadas para ler `/var/log/audit.log` e a pasta monitorada

---

## 🙋 Suporte
Para dúvidas, sugestões ou problemas, entre em contato com o mantenedor do projeto.

