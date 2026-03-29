#!/bin/bash

WIFI_NAME="preconfigured"
AP_NAME="logger-ap"

# check internet (of gateway)
ping -c 2 8.8.8.8 > /dev/null

if [ $? -ne 0 ]; then
    echo "Geen wifi → AP starten"
    nmcli con down "$WIFI_NAME"
    nmcli con up "$AP_NAME"
else
    echo "Wifi OK"
    nmcli con down "$AP_NAME" 2>/dev/null
    nmcli con up "$WIFI_NAME"
fi

# automatisch laten werken
# Crontab -e
# */1 * * * * /home/pi/wifi_fallback.sh