import os
import sys
from config import LOCKFILE

def criar_lockfile():
    if os.path.exists(LOCKFILE):
        print("⚠️ Já existe uma instância do bot rodando. Abortando.")
        sys.exit(1)
    with open(LOCKFILE, "w") as f:
        f.write(str(os.getpid()))

def remover_lockfile():
    if os.path.exists(LOCKFILE):
        os.remove(LOCKFILE)