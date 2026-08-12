#!/bin/sh
set -eu

for profile in pma bga mo; do
  destination="/opt/data/profiles/$profile"
  mkdir -p "$destination"
  cp -R "/bundles/$profile/." "$destination/"
  mkdir -p "$destination/sessions" "$destination/logs" "$destination/home"
done
chmod 700 /opt/data /opt/data/profiles /opt/data/profiles/pma /opt/data/profiles/bga /opt/data/profiles/mo
chown -R 10000:10000 /opt/data
