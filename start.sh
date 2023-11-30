#! /bin/bash
cd /home/pi/homeautomation/Tibber2Mqtt
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 Tibber2Mqtt.py