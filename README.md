<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/dark_logo.png">
    <img src="assets/logo.png" alt="Diyanet Ezan" width="460">
  </picture>
</p>

# Diyanet Ezan for Home Assistant

Official Diyanet (Türkiye) prayer times in Home Assistant, the same times you see on [namazvakti.diyanet.gov.tr](https://namazvakti.diyanet.gov.tr). No YAML needed: pick your country, city and district from the setup dialog and the sensors appear. Optionally, the integration plays the ezan on your speakers too.

The times come from [ezanvakti.emushaf.net](https://ezanvakti.emushaf.net), an API by Furkan Tektas that mirrors Diyanet's own table.

## Installation

### HACS (recommended)

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/lasharor/Diyanet-Ezan` with category **Integration**.
3. Search for **Diyanet Ezan**, install it, and restart Home Assistant.

### Manual

Copy `custom_components/diyanet_ezan` into the `custom_components` folder of your Home Assistant config and restart.

## Setup

**Settings → Devices & services → Add integration → Diyanet Ezan**, then choose your country, city and district. Countries with a single city level (such as the Netherlands) skip straight to the district list. You can add several districts if you want times for more than one place.

## Ezan on your speakers (optional)

Open **Settings → Devices & services → Diyanet Ezan → Configure** to have the integration play the ezan itself, without writing an automation:

| Option | What it does |
|---|---|
| Speakers | The media players to play on. Leave empty to keep playback off. |
| Ezan audio | What to play, e.g. `media-source://media_source/local/ezan.mp3` for a file in your `media` folder. A local file is more reliable than a web URL. |
| Volume | Sets this volume first. Leave empty to keep each speaker's volume. |
| Play at | Which times to play: İmsak, Sabah, Öğle, İkindi, Akşam, Yatsı. |
| Morning ezan | Sabah plays this many minutes before Güneş (default 35). |
| Only when someone is home | Skips playback when `zone.home` shows nobody is home. |
| Play as announcement | Pauses music and resumes it after the ezan, on speakers that support it. |
| Ramadan sahur alarm | During Ramazan, plays this many minutes before İmsak (0 = off), with its own audio if you like. |

When speakers are set, two extra entities appear:

- `switch.diyanet_ezan_playback`: turn it off to mute the ezan, for example during a call. It remembers its state across restarts.
- `button.diyanet_ezan_play_now`: plays the ezan right away, handy to test speakers and volume.

Mute during a Teams call, for example:

```yaml
- alias: Mute ezan during calls
  triggers:
    - trigger: state
      entity_id: sensor.teams_activity
  actions:
    - action: "switch.turn_{{ 'off' if trigger.to_state.state == 'In a call' else 'on' }}"
      target:
        entity_id: switch.diyanet_ezan_playback
```

Notifications to your phone or TV aren't built in; use the `diyanet_ezan_prayer` event below for those.

## Entities

Entity IDs below are what you get with Home Assistant set to English. Check the **Diyanet Ezan** device page for the exact IDs on your system.

| Entity | What it shows |
|---|---|
| `sensor.diyanet_ezan_imsak` | İmsak time today |
| `sensor.diyanet_ezan_gunes` | Güneş (sunrise) |
| `sensor.diyanet_ezan_ogle` | Öğle |
| `sensor.diyanet_ezan_ikindi` | İkindi |
| `sensor.diyanet_ezan_aksam` | Akşam |
| `sensor.diyanet_ezan_yatsi` | Yatsı |
| `sensor.diyanet_ezan_next_prayer` | Time of the next prayer (attribute `prayer` holds its name) |
| `sensor.diyanet_ezan_next_prayer_name` | Name of the next prayer (`imsak`, `gunes`, `ogle`, …) |
| `sensor.diyanet_ezan_time_remaining` | Minutes until the next prayer |
| `sensor.diyanet_ezan_hijri_date` | Hijri date, e.g. `8 Cemaziyelevvel 1448` |
| `binary_sensor.diyanet_ezan_ramadan` | On during Ramazan |

The time sensors are real timestamps, so the dashboard shows them in your own time format and you can trigger automations on them directly. After Yatsı the next prayer rolls over to tomorrow's İmsak.

The logo shows in Home Assistant 2026.3 and newer.

Times are refreshed twice a day and cached on disk, so a restart or a short API outage doesn't leave you without times.

## Automations

### Your own ezan automation

If you'd rather build playback yourself (different speakers per prayer, notifications, and so on), leave the speakers option empty and use the event. The integration fires a `diyanet_ezan_prayer` event at the minute of each time, with `prayer`, `district` and `ramadan` in the event data. One trigger covers all of them:

```yaml
- id: ezan
  alias: Ezan
  triggers:
    - trigger: event
      event_type: diyanet_ezan_prayer
  conditions:
    - condition: template   # skip Güneş; it's sunrise, not a prayer
      value_template: "{{ trigger.event.data.prayer != 'gunes' }}"
    - condition: numeric_state   # someone is home
      entity_id: zone.home
      above: 0
  actions:
    - action: media_player.play_media
      target:
        entity_id: media_player.living_room
      data:
        media_content_id: media-source://media_source/local/ezan.mp3
        media_content_type: music
        announce: true
```

### Trigger before a time (sabah, sahur)

Use a time trigger with an offset. For example, 35 minutes before sunrise for sabah, or 40 minutes before İmsak to wake up for sahur:

```yaml
triggers:
  - trigger: time
    at:
      entity_id: sensor.diyanet_ezan_imsak
      offset: "-00:40:00"
conditions:
  - condition: state
    entity_id: binary_sensor.diyanet_ezan_ramadan
    state: "on"
```

### Ask a voice assistant how long until the next prayer

```yaml
- action: tts.speak
  target:
    entity_id: tts.google_translate_en_com
  data:
    media_player_entity_id: media_player.living_room
    message: >-
      {% set m = states('sensor.diyanet_ezan_time_remaining') | int(0) %}
      {{ state_attr('sensor.diyanet_ezan_next_prayer', 'prayer') | capitalize }}
      in {{ m // 60 }} hours and {{ m % 60 }} minutes.
```

## Dashboard card

A compact card with the next prayer, a countdown, and a fold-out row with all five times. Needs [Mushroom](https://github.com/piitaya/lovelace-mushroom), [card-mod](https://github.com/thomasloven/lovelace-card-mod), [stack-in-card](https://github.com/custom-cards/stack-in-card) and [layout-card](https://github.com/thomasloven/lovelace-layout-card), plus a helper `input_boolean.prayer_dropdown` for the fold-out. The mute button uses the playback switch from the options above.

```yaml
type: custom:stack-in-card
cards:
  - type: custom:layout-card
    layout_type: custom:grid
    layout:
      grid-template-columns: auto 120px
      margin: -4px 0px -10px -4px
    cards:
      - type: custom:mushroom-template-card
        entity: sensor.diyanet_ezan_next_prayer
        primary: Namaz
        secondary: >-
          {% set m = states('sensor.diyanet_ezan_time_remaining') | int(0) %}
          {{ as_timestamp(states(entity)) | timestamp_custom('%H:%M') }}
          | {{ '%d:%02d' | format(m // 60, m % 60) }} to go
        icon: mdi:hands-pray
        icon_color: grey
        tap_action:
          action: none
        card_mod:
          style: |
            ha-card { --ha-card-box-shadow: none; }
      - type: custom:stack-in-card
        mode: horizontal
        card_mod:
          style: |
            ha-card { --ha-card-box-shadow: none; }
        cards:
          - type: custom:mushroom-template-card
            entity: switch.diyanet_ezan_playback
            icon: "{{ 'mdi:volume-high' if is_state(entity, 'on') else 'mdi:volume-off' }}"
            icon_color: "{{ 'green' if is_state(entity, 'on') else 'red' }}"
            tap_action:
              action: toggle
          - type: custom:mushroom-template-card
            entity: input_boolean.prayer_dropdown
            icon: "{{ 'mdi:chevron-up' if is_state(entity, 'on') else 'mdi:chevron-down' }}"
            icon_color: disabled
            tap_action:
              action: toggle
  - type: conditional
    conditions:
      - condition: state
        entity: input_boolean.prayer_dropdown
        state: "on"
    card:
      type: grid
      columns: 5
      square: false
      cards:
        - &prayer
          type: custom:mushroom-template-card
          entity: sensor.diyanet_ezan_imsak
          primary: İmsak
          secondary: "{{ as_timestamp(states(entity)) | timestamp_custom('%H:%M') }}"
          icon: mdi:weather-night-partly-cloudy
          icon_color: "{{ 'disabled' if as_timestamp(states(entity)) < as_timestamp(now()) else 'amber' }}"
          layout: vertical
          tap_action:
            action: none
          card_mod:
            style: |
              ha-card { --ha-card-box-shadow: none; }
        - <<: *prayer
          entity: sensor.diyanet_ezan_ogle
          primary: Öğle
          icon: mdi:white-balance-sunny
        - <<: *prayer
          entity: sensor.diyanet_ezan_ikindi
          primary: İkindi
          icon: mdi:weather-partly-cloudy
        - <<: *prayer
          entity: sensor.diyanet_ezan_aksam
          primary: Akşam
          icon: mdi:weather-sunset-down
        - <<: *prayer
          entity: sensor.diyanet_ezan_yatsi
          primary: Yatsı
          icon: mdi:weather-night
```

Paste it through the dashboard's raw configuration editor; it expands the `<<: *prayer` shortcuts into five full cards when it saves.

## Upgrading from the YAML guide

If you used the earlier `rest:` and `template:` setup, remove those blocks from `configuration.yaml` after installing this integration, and point your automations and cards at the new entity IDs above. The old `…_vakti` true/false sensors aren't needed any more. Your speaker automation can usually go too: set the speakers in **Configure**, and replace `input_boolean.disableprayer` with `switch.diyanet_ezan_playback` (note: on means *play*, the opposite of the old helper).

## Support

Open an [issue](https://github.com/lasharor/Diyanet-Ezan/issues) for bugs or feature requests.

## License

MIT
