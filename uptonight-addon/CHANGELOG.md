# Changelog

## 2.8.0

- Add an **Observation max hours** option to cap the observing window length.
  Useful for long winter or polar-night windows that would otherwise produce a
  cluttered plot. Leave blank for no limit.
- Add an add-on icon.

## 2.7.0

- Initial release. Run UpTonight from Home Assistant with UI-based
  configuration: coordinates (WGS84 decimal degrees), feature toggles, and an
  optional observation date. The MQTT broker details are taken automatically
  from Home Assistant's MQTT service. Runs once on demand (e.g. from a daily
  automation) and publishes the results over MQTT.
