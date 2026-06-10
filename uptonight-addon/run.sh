#!/usr/bin/env bash
# Bridge between Home Assistant add-on options and UpTonight's config.yaml.
#
# Reads the add-on options (bashio::config) and the MQTT broker details from
# Home Assistant's service (bashio::services), generates the config UpTonight
# expects as JSON (valid YAML for yaml.safe_load), then launches UpTonight.
#
# NOTE: `set -u` is intentionally omitted - bashio is not guaranteed to be
# unset-variable clean when sourced. Required values are validated explicitly.
set -eo pipefail

# shellcheck source=/dev/null
source "${BASHIO_LIB:-/usr/lib/bashio/lib/bashio.sh}"

CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"
# Persistent output (host: /addon_configs/<slug>/out). OUTPUT_DIR overrides
# UpTonight's /app-relative output_dir.
export OUTPUT_DIR="${OUTPUT_DIR:-/config/out}"
mkdir -p "${OUTPUT_DIR}"

# Decimal number (optionally signed/fractional), used to validate coordinates.
readonly NUMBER_RE='^-?[0-9]+(\.[0-9]+)?$'

# --- Location: latitude/longitude are required; the rest have defaults --------
LATITUDE="$(bashio::config 'latitude')"
LONGITUDE="$(bashio::config 'longitude')"

if ! [[ "${LATITUDE}" =~ ${NUMBER_RE} ]]; then
  bashio::log.error "Option 'latitude' must be a decimal number (WGS84), got: '${LATITUDE}'."
  bashio::exit.nok "Set 'latitude' in the add-on configuration."
fi
if ! [[ "${LONGITUDE}" =~ ${NUMBER_RE} ]]; then
  bashio::log.error "Option 'longitude' must be a decimal number (WGS84), got: '${LONGITUDE}'."
  bashio::exit.nok "Set 'longitude' in the add-on configuration."
fi

ELEVATION="$(bashio::config 'elevation')"
bashio::config.has_value 'elevation' || ELEVATION=0

TIMEZONE="$(bashio::config 'timezone')"
bashio::config.has_value 'timezone' || TIMEZONE="${TZ:-UTC}"

OBSERVATORY_NAME="$(bashio::config 'observatory_name')"
bashio::config.has_value 'observatory_name' || OBSERVATORY_NAME="Home"

# --- Build the base config as JSON (a valid YAML document) --------------------
config="$(jq -n \
  --argjson latitude "${LATITUDE}" \
  --argjson longitude "${LONGITUDE}" \
  --argjson elevation "${ELEVATION}" \
  --arg timezone "${TIMEZONE}" \
  --arg observatory_name "${OBSERVATORY_NAME}" \
  --argjson objects "$(bashio::config 'objects')" \
  --argjson bodies "$(bashio::config 'bodies')" \
  --argjson comets "$(bashio::config 'comets')" \
  --argjson horizon "$(bashio::config 'horizon')" \
  --argjson alttime "$(bashio::config 'alttime')" \
  '{
    location: {
      latitude: $latitude,
      longitude: $longitude,
      elevation: $elevation,
      timezone: $timezone,
      observatory_name: $observatory_name
    },
    features: {
      objects: $objects,
      bodies: $bodies,
      comets: $comets,
      horizon: $horizon,
      alttime: $alttime
    }
  }')"

# --- Optional observation date (blank = tonight) -----------------------------
if bashio::config.has_value 'observation_date'; then
  config="$(jq --arg d "$(bashio::config 'observation_date')" '. + {observation_date: $d}' <<<"${config}")"
fi

# --- Optional cap on the observing window length (hours) ----------------------
if bashio::config.has_value 'observation_max_hours'; then
  config="$(jq --argjson hours "$(bashio::config 'observation_max_hours')" \
    '. + {constraints: {observation_max_hours: $hours}}' <<<"${config}")"
fi

# --- MQTT from the Home Assistant service (omit if none is offered) ----------
if bashio::services.available 'mqtt'; then
  mqtt_host="$(bashio::services 'mqtt' 'host')"
  mqtt_port="$(bashio::services 'mqtt' 'port')"
  [[ "${mqtt_port}" =~ ^[0-9]+$ ]] || mqtt_port=1883

  config="$(jq --arg host "${mqtt_host}" --argjson port "${mqtt_port}" \
    '. + {mqtt: {host: $host, port: $port, clientid: "uptonight"}}' <<<"${config}")"

  # Username/password are absent for an anonymous broker - only add real values
  # (never the literal "null" bashio returns for a missing service field).
  mqtt_user="$(bashio::services 'mqtt' 'username')"
  if [ -n "${mqtt_user}" ] && [ "${mqtt_user}" != "null" ]; then
    config="$(jq --arg user "${mqtt_user}" '.mqtt += {user: $user}' <<<"${config}")"
  fi
  mqtt_password="$(bashio::services 'mqtt' 'password')"
  if [ -n "${mqtt_password}" ] && [ "${mqtt_password}" != "null" ]; then
    config="$(jq --arg password "${mqtt_password}" '.mqtt += {password: $password}' <<<"${config}")"
  fi

  bashio::log.info "MQTT broker configured from the Home Assistant service."
else
  bashio::log.warning "No MQTT service available - running without publishing."
fi

echo "${config}" >"${CONFIG_PATH}"
bashio::log.info "Wrote UpTonight configuration to ${CONFIG_PATH}."

# Dry-run hook for tests: generate the config but do not launch UpTonight.
if [ "${ADDON_DRY_RUN:-0}" = "1" ]; then
  exit 0
fi

exec /app/main
