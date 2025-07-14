#!/bin/bash

echo "========================================"
echo "   AI Chat Platform - Backend Locale"
echo "========================================"
echo

# Controlla se Python è installato
if ! command -v python3 &> /dev/null; then
    echo "ERRORE: Python3 non trovato!"
    echo "Su Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "Su macOS: brew install python"
    exit 1
fi

echo "Python trovato! Versione:"
python3 --version
echo

# Controlla se siamo nella cartella giusta
if [ ! -d "src" ]; then
    echo "ERRORE: Cartella 'src' non trovata!"
    echo "Assicurati di essere nella cartella 'backend' del progetto"
    exit 1
fi

echo "Controllo ambiente virtuale..."
if [ ! -d "venv" ]; then
    echo "Creazione ambiente virtuale..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERRORE: Impossibile creare ambiente virtuale"
        exit 1
    fi
    echo "Ambiente virtuale creato!"
fi

echo "Attivazione ambiente virtuale..."
source venv/bin/activate

echo "Installazione/aggiornamento dipendenze..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERRORE: Impossibile installare dipendenze"
    exit 1
fi

echo
echo "========================================"
echo "     AVVIO DEL BACKEND IN CORSO..."
echo "========================================"
echo
echo "Il backend sarà disponibile su:"
echo "  http://localhost:5000"
echo
echo "Per fermare il server, premi Ctrl+C"
echo

cd src
python main.py

echo
echo "Backend fermato."

