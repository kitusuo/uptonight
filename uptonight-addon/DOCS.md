# UpTonight — Home Assistant Add-on

Runs [UpTonight](https://github.com/kitusuo/uptonight) inside Home Assistant:
it calculates the best astrophotography targets for the night at your location
and publishes the results (sensors + a sky-plot image) to Home Assistant over
MQTT. It is a one-shot job — it runs, publishes, and exits.

## Installation

1. Settings → Add-ons → Add-on Store → ⋮ → **Repositories**.
2. Add `https://github.com/kitusuo/uptonight` and close.
3. Find **UpTonight** in the store and click **Install**.

The add-on installs with the slug `<repository-hash>_uptonight` (see
[Find the add-on slug](#find-the-add-on-slug) below).

## Configuration

All configuration is done in the add-on's **Configuration** tab — there is no
file to hand-edit.

| Option | Required | Default | Notes |
| --- | --- | --- | --- |
| `latitude` | yes | – | WGS84 decimal degrees, e.g. `61.4978` |
| `longitude` | yes | – | WGS84 decimal degrees, e.g. `23.7610` |
| `elevation` | no | `0` | Metres above sea level |
| `timezone` | no | container `TZ` / `UTC` | e.g. `Europe/Helsinki` |
| `observatory_name` | no | `Home` | Used in the MQTT entity names (`uptonight_<name>_…`) |
| `observation_date` | no | tonight | `mm/dd/yy`, e.g. `06/21/26` — handy for testing |
| `observation_max_hours` | no | no limit | Cap the observing window length (hours); shortens long winter/polar-night windows for a readable plot |
| `objects` | – | `true` | Deep-sky objects |
| `bodies` | – | `true` | Sun/Moon/planets |
| `comets` | – | `false` | Comets (downloads the MPC catalogue) |
| `horizon` | – | `false` | Custom horizon overlay |
| `alttime` | – | `false` | Per-target altitude/time plots |

### MQTT

Declare an MQTT broker in Home Assistant (e.g. the *Mosquitto broker* add-on).
The broker host, port, username and password are passed to UpTonight
automatically via the `mqtt` service — **you never enter them here**. If no MQTT
service is available, the add-on still runs and writes its output, just without
publishing.

## Running

The add-on uses `startup: once` / `boot: manual`: it runs to completion and
exits. Start it manually from the **Info** tab, or — more usefully — run it on a
schedule with an automation.

### Find the add-on slug

The `hassio.addon_start` action needs the add-on's slug. Open the add-on
(Settings → Add-ons → **UpTonight**) and read it from the page URL:

```
http://homeassistant.local:8123/hassio/addon/347b6192_uptonight/info
                                              ^^^^^^^^^^^^^^^^^^ this is the slug
```

The `347b6192` prefix is a hash Home Assistant derives from this repository's
URL, so **copy the exact value from your own add-on's URL** — it is stable once
installed.

### Recommended: run it daily

Pick a time in the afternoon so the results are ready before nightfall.

```yaml
alias: UpTonight daily calculation
description: ""
triggers:
  - trigger: time
    at: "13:00:00"
conditions: []
actions:
  - action: hassio.addon_start
    data:
      addon: 347b6192_uptonight  # replace with the slug from your add-on URL
mode: single
```

## Output

Generated plots and reports are written to the add-on's persistent config
directory (`/addon_configs/<slug>/out` on the host). The sky plot and sensor
states are also published to Home Assistant over MQTT.
