# Changelog

## [2.0.0] - 2026-10-19

### Changed
- Rewritten as a HACS custom integration with UI setup (country → city → district).
  The earlier add-on called API endpoints that don't exist and has been removed.

### Added
- Timestamp sensors for İmsak, Güneş, Öğle, İkindi, Akşam and Yatsı.
- Next prayer (time and name), minutes remaining, Hijri date and a Ramadan binary sensor.
- `diyanet_ezan_prayer` event fired at each prayer time.
- On-disk cache so restarts and short API outages keep working.
- Optional ezan playback on speakers, set up under Configure: speakers, audio, volume,
  which times, morning ezan offset before Güneş, only-when-home, announce mode, and a
  Ramadan sahur alarm. Adds a playback switch (mute) and a Play now button.
- Logo and icon, shown in Home Assistant 2026.3 and newer.
- English, Dutch and Turkish translations.

## [2026-03-04]
- Initial release of Diyanet Ezan.
