# TheNoodleSnoop
*The clumsy but occasionally useful sidekick of [TheSpaghettiDetective](https://github.com/TheSpaghettiDetective).*

## Introduction
TheNoodleSnoop borrows the pre-trained neural network from [obico-server](https://github.com/TheSpaghettiDetective/obico-server) along with some utility functions,
and strips away everything else like the web server and GUI. Instead, it uses MQTT to report any findings.

It is configured with the snapshot URL of your camera, and reports findings and the snapshot with detection overlay
via MQTT. The user can then handle the message as they prefer, for example in Home Assistant.

## Pre-requisites

- Docker installation
- Powerful enough host to run the server

## Configuration
Set camera source and MQTT settings in `docker-compose.yml`.

Recommended to create a `.env` file in the same directory as `docker-compose.yml` for secrets to prevent
accidentally pushing them to public repositories.

Example `.env` file:
```
SNAPSHOT_URL=192.168.1.25:8080/snapshot
MQTT_BROKER_IP=192.168.1.4
MQTT_BROKER_PORT=1883
MQTT_BROKER_USER=my-ha-mqtt-user
MQTT_BROKER_PASSWORD=my-ha-mqtt-password
```

## Installation
```
docker-compose up -d
```

## Home Assistant Integration
Use the [MQTT Camera](https://www.home-assistant.io/integrations/camera.mqtt/) integration to show the detection overlay.

Example configuration:
```
mqtt:
  camera:
    - topic: thenoodlesnoop/overlay
      name: Bambu Lab P1S NoodleCam
      image_encoding: b64
```

Use [Notify](https://www.home-assistant.io/integrations/notify/) integration for custom notifications about failures.

Example automation:
```
TBA
```

Use [ha-bambulab](https://github.com/greghesp/ha-bambulab) custom component for controlling the printer based on detections

Example automation:
```
TBA
```

MQTT Camera does not seem to support `value_template`s, which is the whole reason there is currently a separate
`MQTT_OVERLAY_TOPIC` which you can use in the configuration.

## API Reference

### `${MQTT_BASE_TOPIC}/detections`

#### payload
```
{
    'failing': <TheNoodleSnoop's opinion whether print is failing [bool]>,
    'raw_detections': <all detections with confidences and locations [list]>,
    'raw_predictions': <some data about predictions [dict]>,
    'overlay': <utf-8 representation of base64 encoded image [string]>,
    'timestamp': <unix timestamp [float]>
}
```

### `${MQTT_BASE_TOPIC}/overlay`
Convenience topic until I figure out how to use something like `value_template` in Home Assistant MQTT Camera integration.
Payload is the same as `payload['overlay']` in `MQTT_REPORT_TOPIC`.

#### payload
```
<utf-8 representation of base64 encoded image [string]>
```


### `${MQTT_BASE_TOPIC}/control`
Not implemented. Start, stop, re-configuration, etc.