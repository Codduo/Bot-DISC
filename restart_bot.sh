#!/bin/bash

echo "🔄 Parando bot..."
sudo pkill -f "python.*bot.py"
sudo systemctl stop bot-disc
sleep 2

echo "📥 Fazendo git pull..."
git pull

echo "🚀 Reiniciando bot..."
sudo systemctl start bot-disc
sleep 3

echo "📊 Status do bot:"
sudo systemctl status bot-disc --no-pager -l