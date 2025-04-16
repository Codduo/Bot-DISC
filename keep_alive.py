from flask import Flask
from threading import Thread
import time
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot está online e ativo!"

def run_server():
    app.run(host="0.0.0.0", port=8080)

def ping_self():
    while True:
        try:
            requests.get("http://localhost:8080/")
            print("🔁 Auto-ping enviado com sucesso.")
        except Exception as e:
            print(f"⚠️ Erro no auto-ping: {e}")
        time.sleep(50)

def keep_alive():
    t1 = Thread(target=run_server)
    t2 = Thread(target=ping_self)
    t1.start()
    t2.start()
