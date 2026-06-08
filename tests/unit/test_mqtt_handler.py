"""MQTTHandler connection lifecycle.

paho's ``Client`` is the third-party collaborator; we replace it with a small
fake that invokes the registered ``on_connect`` callback with a chosen CONNACK
return code, so the connect handshake can be driven without a real broker.
"""

import pytest

import uptonight.mqtthandler as mh

NOT_AUTHORIZED = 5


class FakePaho:
    """Minimal paho stand-in that simulates a CONNACK with a given return code."""

    def __init__(self, connack_rc):
        self._connack_rc = connack_rc
        self.on_connect = None
        self.on_disconnect = None
        self.disconnect_called = False

    def username_pw_set(self, *args, **kwargs):
        pass

    def will_set(self, *args, **kwargs):
        pass

    def connect(self, host, port):
        # The broker's response arrives via the on_connect callback.
        self.on_connect(self, None, {}, self._connack_rc, None)

    def loop_forever(self):
        pass

    def disconnect(self):
        self.disconnect_called = True

    def publish(self, *args, **kwargs):
        return None


@pytest.fixture
def patch_paho(monkeypatch):
    def _install(connack_rc):
        monkeypatch.setattr(mh.time, "sleep", lambda *_: None)
        monkeypatch.setattr(mh.mqtt, "Client", lambda *args, **kwargs: FakePaho(connack_rc))

    return _install


def test_successful_connection_marks_handler_connected(patch_paho):
    patch_paho(0)
    handler = mh.MQTTHandler({"host": "broker", "port": 1883})

    handler.connect()

    assert handler.connected() is True


def test_rejected_connection_raises_connection_error(patch_paho):
    # Regression: the failure path used to call a non-existent shutdown().
    patch_paho(NOT_AUTHORIZED)
    handler = mh.MQTTHandler({"host": "broker", "port": 1883})

    with pytest.raises(ConnectionError):
        handler.connect()


def test_rejected_connection_does_not_mark_connected(fake_mqtt_client):
    handler = mh.MQTTHandler({"host": "broker", "port": 1883})

    handler.on_mqtt_connect(fake_mqtt_client, None, {}, NOT_AUTHORIZED, None)

    assert handler.connected() is False


def test_on_disconnect_marks_handler_disconnected(fake_mqtt_client):
    handler = mh.MQTTHandler({"host": "broker", "port": 1883})
    handler.on_mqtt_connect(fake_mqtt_client, None, {}, 0, None)

    handler.on_mqtt_disconnect(fake_mqtt_client, None, 0, None)

    assert handler.connected() is False


def test_disconnect_delegates_to_the_client(fake_mqtt_client):
    handler = mh.MQTTHandler({"host": "broker", "port": 1883})
    handler._mqttclient = fake_mqtt_client

    handler.disconnect()

    assert fake_mqtt_client.disconnect_called is True
