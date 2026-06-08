"""MQTTDeviceHandler: discovery config and the publish message kinds.

The handler takes its MQTT client by injection, so tests drive it with the
``fake_mqtt_client`` spy and assert on the recorded publishes (state
verification), never on how paho was called internally.
"""

import json
import queue

import pytest

from uptonight.const import DEVICE_TYPE_CAMERA, DEVICE_TYPE_UPTONIGHT, FUNCTIONS
from uptonight.mqtthandler import MQTTDeviceHandler

TOPIC_PREFIX = "uptonight/obs_objects_garyimm/"


def _device(device_type):
    return {
        "observatory": "Obs",
        "type": "Objects",
        "catalogue": "GaryImm",
        "device_type": device_type,
        "functions": list(FUNCTIONS[device_type]),
    }


def _state_message(table=None, darkness="None"):
    return {
        "uptonight_table": table if table is not None else [],
        "darkness": darkness,
        "observatory": "Obs",
        "site_longitude": 1.0,
        "site_latitude": 2.0,
        "elevation": 3.0,
        "astronight_from": "from",
        "astronight_to": "to",
        "moon_illumination": 50,
        "altitude_constraint_min": 30,
        "altitude_constraint_max": 80,
        "airmass_constraint": 2,
        "moon_separation": 45,
        "size_constraint_min": 1,
        "size_constraint_max": 9,
    }


@pytest.fixture
def camera_handler(fake_mqtt_client):
    return MQTTDeviceHandler(fake_mqtt_client, queue.Queue(), _device(DEVICE_TYPE_CAMERA))


@pytest.fixture
def sensor_handler(fake_mqtt_client):
    return MQTTDeviceHandler(fake_mqtt_client, queue.Queue(), _device(DEVICE_TYPE_UPTONIGHT))


# --- discovery config --------------------------------------------------------


def test_image_config_uses_a_dedicated_availability_topic(camera_handler, fake_mqtt_client):
    camera_handler.create_mqtt_config()

    config = json.loads(fake_mqtt_client.payload_for("/config"))
    assert config["availability_topic"] == TOPIC_PREFIX + "screen_availability"


def test_sensor_config_is_published_retained_at_qos_1(sensor_handler, fake_mqtt_client):
    sensor_handler.create_mqtt_config()

    config_publish = fake_mqtt_client.published_to("/config")[0]
    assert (config_publish.qos, config_publish.retain) == (1, True)


def test_config_publishes_are_awaited(camera_handler, fake_mqtt_client):
    camera_handler.create_mqtt_config()

    assert all(info.wait_for_publish_called for info in fake_mqtt_client.infos)


# --- publish_device message kinds -------------------------------------------


def test_no_darkness_publishes_image_offline_without_a_screen(camera_handler, fake_mqtt_client):
    camera_handler.publish_device({"image_available": "OFF"})

    availability = fake_mqtt_client.published_to("/screen_availability")[0]
    assert (availability.payload, availability.qos, availability.retain) == ("OFF", 1, True)
    assert fake_mqtt_client.published_to("/screen") == []


def test_image_available_message_drives_only_the_availability_topic(camera_handler, fake_mqtt_client):
    camera_handler.publish_device({"image_available": "ON"})

    assert fake_mqtt_client.payload_for("/screen_availability") == "ON"
    assert fake_mqtt_client.published_to("/state") == []


def test_screen_message_publishes_image_bytes_retained(camera_handler, fake_mqtt_client):
    camera_handler.publish_device({"screen": b"PNGDATA"})

    screen = fake_mqtt_client.published_to("/screen")[0]
    assert (screen.payload, screen.qos, screen.retain) == (b"PNGDATA", 1, True)


def test_state_message_publishes_target_count(sensor_handler, fake_mqtt_client):
    sensor_handler.publish_device(_state_message(table=[{"a": 1}, {"b": 2}]))

    state = json.loads(fake_mqtt_client.payload_for("/state"))
    assert state == {"garyimm": 2}


def test_state_message_carries_darkness_in_attributes(sensor_handler, fake_mqtt_client):
    sensor_handler.publish_device(_state_message(table=[], darkness="None"))

    attributes = json.loads(fake_mqtt_client.payload_for("/attributes"))
    assert attributes["darkness"] == "None"


def test_sensor_availability_is_published_online(sensor_handler, fake_mqtt_client):
    sensor_handler.publish_device(_state_message())

    assert fake_mqtt_client.payload_for("/lwt") == "ON"


def test_publishes_are_awaited_before_returning(sensor_handler, fake_mqtt_client):
    sensor_handler.publish_device(_state_message())

    assert all(info.wait_for_publish_called for info in fake_mqtt_client.infos)


def test_looper_drains_the_message_queue(fake_mqtt_client):
    message_queue = queue.Queue()
    message_queue.put({"image_available": "ON"})
    message_queue.put({"screen": b"PNG"})
    handler = MQTTDeviceHandler(fake_mqtt_client, message_queue, _device(DEVICE_TYPE_CAMERA))

    handler.looper()

    assert message_queue.empty()
    assert fake_mqtt_client.payload_for("/screen") == b"PNG"


def test_wait_for_publish_continues_past_a_timeout(camera_handler):
    class TimingOutInfo:
        def wait_for_publish(self, timeout=None):
            raise RuntimeError("publish timed out")

    class RecordingInfo:
        def __init__(self):
            self.waited = False

        def wait_for_publish(self, timeout=None):
            self.waited = True

    later_info = RecordingInfo()

    camera_handler._wait_for_publish([TimingOutInfo(), later_info])

    assert later_info.waited is True


def test_looper_consumes_the_message_then_stops_on_publish_error(camera_handler):
    from paho.mqtt import MQTTException

    class RaisingClient:
        def publish(self, *args, **kwargs):
            raise MQTTException("broker gone")

    message_queue = queue.Queue()
    message_queue.put({"image_available": "ON"})
    handler = MQTTDeviceHandler(RaisingClient(), message_queue, _device(DEVICE_TYPE_CAMERA))

    handler.looper()

    assert message_queue.empty()

