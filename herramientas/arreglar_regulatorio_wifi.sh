#!/usr/bin/env bash
# Habilita los canales de 5 GHz en un DeepRacer.
#
# QUE ARREGLA
# -----------
# La imagen del DeepRacer viene SIN /lib/firmware/regulatory.db. Sin esa base el
# kernel no tiene reglas de ningun pais, cae al dominio mundial "00" y deja las
# 31 frecuencias de 5 GHz en "no IR" -la radio escucha y no transmite-.
#
# El sintoma es MUDO y por eso cuesta tanto: el vehiculo VE las redes de 5 GHz en
# el barrido, las lista con buena senal, y al conectarse falla sin decir por que.
# Se parece a una contrasena mal puesta o a un punto de acceso caprichoso.
#
# El kernel lo dice en el arranque, y es la unica pista:
#     platform regulatory.0: Direct firmware load for regulatory.db failed
#     cfg80211: failed to load regulatory.db
#
# Encontrado el 2026-10-05 en los DOS vehiculos. Evidencia completa en
# Documentos/Evidencia/S26_red_5ghz_regulatorio.md
#
# QUE HACE
# --------
#   1. Copia regulatory.db y regulatory.db.p7s desde ESTE equipo al vehiculo.
#   2. Instala dominio-regulatorio.service, porque 'iw reg set' no sobrevive al
#      reinicio.
#   3. Reinicia el vehiculo: cfg80211 solo lee la base AL ARRANCAR, asi que
#      recargar el modulo de la tarjeta no sirve.
#   4. Comprueba el resultado y lo imprime.
#
# OJO: NO descargues el modulo mwifiex_pcie estando conectado por SSH sobre esa
# misma tarjeta. Se intento el 5-oct y el vehiculo se quedo sin red hasta que
# NetworkManager reasocio sola. Salio bien y pudo no salir.
#
# USO
#     bash herramientas/arreglar_regulatorio_wifi.sh 192.168.0.102
#
# Hace falta llave SSH instalada en el vehiculo (ssh-copy-id) y sudo sin
# contrasena, que es como estan los dos carros.

set -uo pipefail

CARRO="${1:-}"
if [ -z "$CARRO" ]; then
  echo "uso: $0 <IP-del-vehiculo>" >&2
  exit 2
fi

BASE=/lib/firmware/regulatory.db
if [ ! -f "$BASE" ]; then
  echo "ERROR: no tengo $BASE en este equipo para copiarlo." >&2
  echo "       Instalalo con: sudo apt install wireless-regdb" >&2
  exit 1
fi

ssh_carro() { ssh -o BatchMode=yes -o ConnectTimeout=8 "deepracer@$CARRO" "$@"; }

echo "== antes =="
ssh_carro 'T=$(iw phy 2>/dev/null | grep -cE "5[0-9]{3}(\.[0-9])? MHz")
           N=$(iw phy 2>/dev/null | grep -E "5[0-9]{3}(\.[0-9])? MHz" | grep -c "no IR")
           D=$(iw phy 2>/dev/null | grep -E "5[0-9]{3}(\.[0-9])? MHz" | grep -c "disabled")
           echo "   $(hostname): 5 GHz utilizables $((T-N-D)) de $T"' || {
  echo "ERROR: no se pudo entrar a $CARRO por SSH." >&2; exit 1; }

echo "== copiando la base regulatoria =="
scp -q -o BatchMode=yes "$BASE" "${BASE}.p7s" "deepracer@$CARRO:/tmp/" || {
  echo "ERROR: fallo la copia." >&2; exit 1; }

ssh_carro 'sudo -n cp /tmp/regulatory.db /tmp/regulatory.db.p7s /lib/firmware/ &&
           sudo -n chmod 644 /lib/firmware/regulatory.db* && echo "   instalada"'

echo "== instalando el servicio que fija el dominio en cada arranque =="
ssh_carro 'sudo -n tee /etc/systemd/system/dominio-regulatorio.service >/dev/null <<"UNIT"
[Unit]
# Fija el dominio regulatorio en cada arranque. Sin esto, tras un reinicio el
# dominio vuelve al mundial "00" y los canales de 5 GHz regresan a "no IR".
# Ver Documentos/Evidencia/S26_red_5ghz_regulatorio.md
Description=Dominio regulatorio WiFi = CO (Colombia)
After=network-pre.target
Wants=network-pre.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/iw reg set CO

[Install]
WantedBy=multi-user.target
UNIT
sudo -n systemctl daemon-reload && sudo -n systemctl enable dominio-regulatorio.service >/dev/null 2>&1 && echo "   servicio activado"'

echo "== reiniciando (cfg80211 solo lee la base al arrancar) =="
ssh_carro 'sudo -n sh -c "sleep 1; reboot" >/dev/null 2>&1 &' || true

for i in $(seq 1 20); do
  sleep 10
  if ssh -o BatchMode=yes -o ConnectTimeout=4 "deepracer@$CARRO" true 2>/dev/null; then
    echo "   volvio a los $((i*10))s"
    break
  fi
  printf "."
done
echo

echo "== despues =="
ssh_carro 'echo "   error de carga en el arranque: $(sudo -n dmesg 2>/dev/null | grep -c "failed to load regulatory.db") (0 = bien)"
           T=$(iw phy 2>/dev/null | grep -cE "5[0-9]{3}(\.[0-9])? MHz")
           N=$(iw phy 2>/dev/null | grep -E "5[0-9]{3}(\.[0-9])? MHz" | grep -c "no IR")
           D=$(iw phy 2>/dev/null | grep -E "5[0-9]{3}(\.[0-9])? MHz" | grep -c "disabled")
           echo "   $(hostname): 5 GHz utilizables $((T-N-D)) de $T"
           iw phy 2>/dev/null | grep -E "5(180|200|220|240)\.0 MHz" | sed "s/^[[:space:]]*/      /"'

echo
echo "Si los canales 36 a 48 salen SIN '(no IR)', el arreglo funciono."
