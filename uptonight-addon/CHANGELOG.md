# Changelog

## 2.8.2

- Update dependencies: astropy 8.0.2, numpy 2.5.4, matplotlib 3.11.2,
  pandas 3.1.0 and pytz 2026.5.

## 2.8.1

- Fix comet brightness: the magnitude formula had the Earth and Sun distances
  swapped and an extra factor on the slope parameter, so comet filtering and
  the "brightest comet" pick used wrong values (upstream fix).
- Fix an intermittent crash ("cannot concatenate times unless all locations
  are set") when an unrelated warning occurred while working out tonight's
  darkness.
- Update dependencies, including astropy 8, numpy 2.5, matplotlib 3.11 and
  Pillow 13, plus security updates for urllib3 and certifi.

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
