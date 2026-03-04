# Diyanet Ezan - Home Assistant Add-on

A Home Assistant add-on that provides prayer times (Ezan times) from the Diyanet (Turkish Directorate of Religious Affairs) using the ezanvakti API.

## Features

- Fetches prayer times from https://ezanvakti.emushaf.net API
- Configurable city and country
- REST API endpoints for integration with Home Assistant
- Automatic updates every 6 hours
- Support for multiple architectures (aarch64, amd64, armv7)

## Installation

1. Add this repository to your Home Assistant:
   ```
   https://github.com/lasharor/Diyanet-Ezan
   ```

2. Install the "Diyanet Ezan" add-on from the add-on store

3. Configure the city and country in the add-on options

4. Start the add-on

## Configuration

```yaml
city: Istanbul
country: Turkey
```

### Available Cities

The add-on supports all cities available in the Diyanet API. You can fetch the list of available cities from the `/api/cities` endpoint.

## API Endpoints

### Get Prayer Times
```
GET /api/prayer-times
```

Returns the prayer times for the configured city.

### Get Available Cities
```
GET /api/cities
```

Returns a list of all available cities in the API.

### Get Current Configuration
```
GET /api/config
```

Returns the current city and country configuration.

## Prayer Times

The add-on provides the following prayer times:
- **Imsak**: Beginning of fasting period (just before Fajr)
- **Gunes**: Sunrise
- **Ogle**: Noon/Zuhr
- **Ikindi**: Afternoon/Asr
- **Aksam**: Evening/Maghrib
- **Yatsi**: Night/Isha

## Usage with Home Assistant

Once the add-on is running, you can integrate it with Home Assistant using REST sensors or automation:

### Example REST Sensor

```yaml
sensor:
  - platform: rest
    resource: http://localhost:8000/api/prayer-times
    name: Diyanet Prayer Times
    json_attributes:
      - Imsak
      - Gunes
      - Ogle
      - Ikindi
      - Aksam
      - Yatsi
    value_template: '{{ value_json.Ogle }}'
```

## Development

To build and test locally:

```bash
docker build -t diyanet-ezan .
docker run -it -p 8000:8000 diyanet-ezan
```

## License

MIT License

## Support

For issues and feature requests, please open an issue on the GitHub repository.