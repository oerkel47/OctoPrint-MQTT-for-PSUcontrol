# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.events import Events


class mqtt_for_psucontrol(octoprint.plugin.StartupPlugin,
                          octoprint.plugin.ShutdownPlugin,
                          octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.EventHandlerPlugin):

    def __init__(self):
        self.mqtt_publish = lambda *args, **kwargs: None
        self.mqtt_subscribe = lambda *args, **kwargs: None
        self.mqtt_unsubscribe = lambda *args, **kwargs: None

        # ~~~~~ will be initialized by config ~~~~~~~
        self.isPSUOn = False
        self.mqtt_topic_state = ""
        self.mqtt_topic_control = ""
        self.mqtt_topic_availability = ""
        self.mqtt_message_Off = ""
        self.mqtt_message_On = ""
        self.ha_discovery_enable = False
        self.ha_discovery_switch_name = ""
        self.ha_discovery_device_name = ""
        self.ha_discovery_optimistic = False
        # ~~~~~~~hardcoded~~~~~~~~~
        self.ha_discovery_id = "octoprint_PSUControl_switch"
        self.available = "online"
        self.unavailable = "offline"

    def on_after_startup(self):
        self.get_current_settings()
        mqtt_helpers = self._plugin_manager.get_helpers("mqtt", "mqtt_publish", "mqtt_subscribe", "mqtt_unsubscribe")
        psu_helpers = self._plugin_manager.get_helpers("psucontrol")

        if mqtt_helpers:
            if "mqtt_publish" in mqtt_helpers:
                self.mqtt_publish = mqtt_helpers["mqtt_publish"]
            if "mqtt_subscribe" in mqtt_helpers:
                self.mqtt_subscribe = mqtt_helpers["mqtt_subscribe"]
            if "mqtt_unsubscribe" in mqtt_helpers:
                self.mqtt_unsubscribe = mqtt_helpers["mqtt_unsubscribe"]
        else:
            self._logger.info("mqtt helpers not found..plugin won't work")

        if psu_helpers:      
            if "get_psu_state" in psu_helpers.keys():
                self.get_psu_state = psu_helpers["get_psu_state"]
            if "turn_psu_off" in psu_helpers.keys():
                self.turn_psu_off = psu_helpers["turn_psu_off"]
            if "turn_psu_on" in psu_helpers.keys():
                self.turn_psu_on = psu_helpers["turn_psu_on"]
        else:
            self._logger.info("psucontrol helpers not found..plugin won't work")

        self.isPSUOn = self.get_psu_state()
        self._logger.debug("after startup: psu was {}".format(self.isPSUOn))

        if self.ha_discovery_enable:
            self.init_ha_discovery()

        self.mqtt_subscribe(self.mqtt_topic_control, self._on_mqtt_subscription)
        self.mqtt_publish(self.mqtt_topic_availability, self.available)
        self.mqtt_publish(self.mqtt_topic_state, self.psu_state_to_message())

    def get_current_settings(self):
        self.mqtt_topic_state = self._settings.get(["mqtt_topic_state"])
        self.mqtt_topic_control = self._settings.get(["mqtt_topic_control"])
        self.mqtt_topic_availability = self._settings.get(["mqtt_topic_availability"])
        self.mqtt_message_Off = self._settings.get(["mqtt_message_Off"])
        self.mqtt_message_On = self._settings.get(["mqtt_message_On"])
        self.ha_discovery_enable = self._settings.get_boolean(["ha_discovery_enable"])
        self.ha_discovery_switch_name = self._settings.get(["ha_discovery_switch_name"])
        self.ha_discovery_device_name = self._settings.get(["ha_discovery_device_name"])
        self.ha_discovery_optimistic = self._settings.get(["ha_discovery_optimistic"])

    def print_current_settings(self):
        self._logger.debug("~~~~ current settings: ~~~~~")
        self._logger.debug("mqtt_topic_state = {}".format(self.mqtt_topic_state))
        self._logger.debug("mqtt_topic_control = {}".format(self.mqtt_topic_control))
        self._logger.debug("mqtt_topic_availability = {}".format(self.mqtt_topic_availability))
        self._logger.debug("mqtt_message_Off = {}".format(self.mqtt_message_Off))
        self._logger.debug("mqtt_message_On = {}".format(self.mqtt_message_On))
        self._logger.debug("HA discovery = {}".format(self.ha_discovery_enable))
        self._logger.debug("ha_discovery_switch_name = {}".format(self.ha_discovery_switch_name))
        self._logger.debug("ha_discovery_device_name = {}".format(self.ha_discovery_device_name))
        self._logger.debug("ha_discovery_optimistic = {}".format(self.ha_discovery_optimistic))
        self._logger.debug("~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    def _on_mqtt_subscription(self, topic, message, retained=None, qos=None, *args, **kwargs):
        self._logger.info("mqtt: received a message for Topic {topic}. Message: {message}".format(**locals()))
        message = message.decode("utf-8")
        self._logger.debug("Message casted into utf-8 string: {}".format(message))
        if message == self.mqtt_message_Off or message == self.mqtt_message_On:
            if message == self.mqtt_message_Off and self.isPSUOn:
                self._logger.debug("relaying OFF command to psucontrol")
                self.turn_psu_off()
            elif message == self.mqtt_message_On and not self.isPSUOn:
                self._logger.debug("relaying ON command to psucontrol")
                # self.mqtt_publish(self.mqtt_topic_state, self.mqtt_message_On)
                # optimistic to counter virtual switch bouncing due to on_delay in PSUControl
                # doesn't work unfortunately
                self.turn_psu_on()
            else:
                self._logger.debug("mqtt: mismatch between local and remote switch states, doing nothing.")
        else:
            self._logger.debug("mqtt: no supported message. Must be {} or {}".format(self.mqtt_message_On,
                                                                                     self.mqtt_message_Off))

    def get_settings_defaults(self):
        return dict(
            mqtt_topic_state="homeassistant/switch/octoprint_PSUControl_switch/state",
            mqtt_topic_control="homeassistant/switch/octoprint_PSUControl_switch/set",
            mqtt_topic_availability="homeassistant/switch/octoprint_PSUControl_switch/availability",
            mqtt_message_Off="OFF",
            mqtt_message_On="ON",
            ha_discovery_enable=False,
            ha_discovery_switch_name="Octoprint PSU Control Switch",
            ha_discovery_device_name="PSUControl on Octoprint",
            ha_discovery_optimistic=False
        )

    def get_settings_version(self):
        return 1

    def on_settings_save(self, data):
        old_mqtt_topic_control = self.mqtt_topic_control
        old_ha_discovery_enable = self.ha_discovery_enable
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.get_current_settings()

        if self.ha_discovery_enable:
            self.mqtt_topic_state = "homeassistant/switch/" + self.ha_discovery_id + "/state"
            self.mqtt_topic_control = "homeassistant/switch/" + self.ha_discovery_id + "/set"
            self.mqtt_topic_availability = "homeassistant/switch/" + self.ha_discovery_id + "/availability"
            self._logger.debug("forcing HA compatible topics..")
            octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
            self.init_ha_discovery()
        elif old_ha_discovery_enable:
            self.init_ha_discovery(mode="disable")

        self.mqtt_subscribe(self.mqtt_topic_control, self._on_mqtt_subscription)
        self.mqtt_unsubscribe(self._on_mqtt_subscription, old_mqtt_topic_control)        
        self.mqtt_publish(self.mqtt_topic_availability, self.available)
        self.mqtt_publish(self.mqtt_topic_state, self.psu_state_to_message())
        self.print_current_settings()

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    def on_event(self, event, payload):
        if event == Events.PLUGIN_PSUCONTROL_PSU_STATE_CHANGED:
            self._logger.debug("detected psu state change event: {}".format(payload))
            if payload["isPSUOn"] == True:
                self._logger.debug("psu was switched on, updating state topic")
                self.isPSUOn = True
            else:
                self._logger.debug("psu was switched off, updating state topic")
                self.isPSUOn = False
            self.mqtt_publish(self.mqtt_topic_state, self.psu_state_to_message())

    def on_shutdown(self):
        self._logger.debug("shutdown..setting switch to unavailable")
        self.mqtt_publish(self.mqtt_topic_availability, self.unavailable)

    def init_ha_discovery(self, mode=None):
        unique_id = self.ha_discovery_id + "_uniqueID"   # unique ID, necessary for autodiscovery
        discoverytopic = "homeassistant/switch/" + self.ha_discovery_id + "/config"
        device_manufacturer = "oerkel47"
        device_model = self._plugin_name

        device = {"name": self.ha_discovery_device_name,
                  "ids": self.ha_discovery_id,
                  "sw_version": "Plugin version " + self._plugin_version,
                  "manufacturer": device_manufacturer,
                  "model": device_model
                  }
        availability = {"topic": self.mqtt_topic_availability,
                        "payload_available": self.available,
                        "payload_not_available": self.unavailable

                        }
        payload = {
                   "device": device,
                   "availability": availability,
                   "name": self.ha_discovery_switch_name,
                   "unique_id": unique_id,
                   "command_topic": self.mqtt_topic_control,
                   "state_topic": self.mqtt_topic_state,
                   "payload_on": self.mqtt_message_On,
                   "payload_off": self.mqtt_message_Off,
                   "optimistic": False
                   }

        if self.ha_discovery_optimistic:
            payload["optimistic"] = True

        if mode == "disable":
            self._logger.debug("Sending empty payload to delete discovery")
            payload = {}
            self.mqtt_publish(discoverytopic, payload)
        else:
            self._logger.debug("Enabling/Updating HA discovery feature")
            self.mqtt_publish(discoverytopic, payload)

        self._logger.debug("HA discovery payload {}".format(payload))

    def psu_state_to_message(self):
        if self.isPSUOn:
            return self.mqtt_message_On
        else:
            return self.mqtt_message_Off

    def get_update_information(self):
        return dict(
            mqtt_for_psucontrol=dict(
                displayName="MQTT for PSU Control",
                displayVersion=self._plugin_version,
                type="github_release",
                current=self._plugin_version,
                user="oerkel47",
                repo="OctoPrint-MQTT-for-PSUcontrol",
                pip="https://github.com/oerkel47/OctoPrint-MQTT-for-PSUcontrol/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "MQTT for PSU Control"
__plugin_pythoncompat__ = ">=3,<4"

def __plugin_load__():
    global __plugin_implementation__
    global __plugin_hooks__

    __plugin_implementation__ = mqtt_for_psucontrol()
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
