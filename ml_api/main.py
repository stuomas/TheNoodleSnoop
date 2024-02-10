import detection_utils
import asyncio
from os import environ
import paho.mqtt.client as mqtt
import socket
import json

client_id = 'TheNoodleSnoop'

MQTT_BROKER_IP = environ.get('MQTT_BROKER_IP')
MQTT_BROKER_PORT = int(environ.get('MQTT_BROKER_PORT'))
MQTT_BROKER_USER = environ.get('MQTT_BROKER_USER')
MQTT_BROKER_PASSWORD = environ.get('MQTT_BROKER_PASSWORD')
MQTT_BASE_TOPIC = environ.get('MQTT_BASE_TOPIC')
MQTT_REPORT_TOPIC = f'{MQTT_BASE_TOPIC}/detections'
MQTT_OVERLAY_TOPIC = f'{MQTT_BASE_TOPIC}/overlay'
MQTT_CONTROL_TOPIC = f'{MQTT_BASE_TOPIC}/control'
SNOOPING_INTERVAL_SEC = int(environ.get('SNOOPING_INTERVAL_SEC'))


class AsyncioHelper:
    def __init__(self, loop, client):
        self.loop = loop
        self.client = client
        self.client.on_socket_open = self.on_socket_open
        self.client.on_socket_close = self.on_socket_close
        self.client.on_socket_register_write = self.on_socket_register_write
        self.client.on_socket_unregister_write = self.on_socket_unregister_write

    def on_socket_open(self, client, userdata, sock):
        def cb():
            client.loop_read()

        self.loop.add_reader(sock, cb)
        self.misc = self.loop.create_task(self.misc_loop())

    def on_socket_close(self, client, userdata, sock):
        self.loop.remove_reader(sock)
        self.misc.cancel()

    def on_socket_register_write(self, client, userdata, sock):
        def cb():
            client.loop_write()

        self.loop.add_writer(sock, cb)

    def on_socket_unregister_write(self, client, userdata, sock):
        self.loop.remove_writer(sock)

    async def misc_loop(self):
        while self.client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break


class AsyncMqttClient:
    def __init__(self, loop):
        self.loop = loop

    def on_connect(self, client, userdata, flags, rc):
        print("Subscribing to control topic")
        client.subscribe(MQTT_CONTROL_TOPIC)

    def on_message(self, client, userdata, msg):
        print("Got message payload: {}".format(msg.payload))

    async def main(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        AsyncioHelper(self.loop, self.client)

        self.client.username_pw_set(MQTT_BROKER_USER, MQTT_BROKER_PASSWORD)
        self.client.connect(MQTT_BROKER_IP, MQTT_BROKER_PORT, 60)
        self.client.socket().setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

        try:
            while True:
                try:
                    payload = detection_utils.get_detections()
                    self.client.publish(MQTT_REPORT_TOPIC, json.dumps(payload), qos=0)
                    self.client.publish(MQTT_OVERLAY_TOPIC, json.dumps(payload['overlay']), qos=0)
                except Exception as ex:
                    print("Exception: ", ex)
                await asyncio.sleep(SNOOPING_INTERVAL_SEC)
        except KeyboardInterrupt:
            print('interrupted!')

        self.client.disconnect()


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(AsyncMqttClient(loop).main())
    loop.close()


if __name__ == "__main__":
    print("Starting")
    main()
    print("Finished")

