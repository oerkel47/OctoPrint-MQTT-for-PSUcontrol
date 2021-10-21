# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
from octoprint.events import Events
from time import sleep


class mqtt_for_psucontrol(octoprint.plugin.StartupPlugin,
                          octoprint.plugin.SettingsPlugin,
                          octoprint.plugin.TemplatePlugin,
                          octoprint.plugin.EventHandlerPlugin,
                          octoprint.plugin.RestartNeedingPlugin):

    def __init__(self):
        # mqtt helpers
        self.mqtt_publish = lambda *args, **kwargs: None
        self.mqtt_subscribe = lambda *args, **kwargs: None
        self.mqtt_unsubscribe = lambda *args, **kwargs: None
        # hardcoded
        self.available = "connected"
        self.unavailable = "disconnected"        
        self.mqtt_topic_availability = "octoPrint/mqtt"
        self.ha_discovery_id = "octoprint_PSUControl_switch"
        self.device_manufacturer = "oerkel47"
        self.unique_id = self.ha_discovery_id + "_uniqueID" 
        self.discoverytopic = "homeassistant/switch/" + self.ha_discovery_id + "/config"       
        # user controllable
        self.config = dict()
        self.mqtt_topic_state = ""
        self.mqtt_topic_control = ""        
        # dynamic
        self.isPSUOn = None

    def on_after_startup(self):
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

        self.reload_settings()
        self.init_ha_discovery()
        
        self.mqtt_subscribe(self.mqtt_topic_control, self._on_mqtt_subscription)
        self.isPSUOn = self.get_psu_state()
        self.mqtt_publish(self.mqtt_topic_state, self.psu_state_to_message())
        self._logger.debug("after startup: psu was {}  ".format(self.psu_state_to_message()))

    def reload_settings(self):
        for k, v in self.get_settings_defaults().items():           
            if type(v) == bool:
                v = self._settings.get_boolean([k])
            else:
                v = self._settings.get([k])

            self.config[k] = v
            self._logger.debug("{}: {}".format(k, v))

        if self.config["ha_discovery_enable"]:  # overwrite values for HA discovery
            self.mqtt_topic_control = "homeassistant/switch/" + self.ha_discovery_id + "/set"
            self.mqtt_topic_state = "homeassistant/switch/" + self.ha_discovery_id + "/state"
        else:
            self.mqtt_topic_control = self.config["mqtt_topic_control"]
            self.mqtt_topic_state = self.config["mqtt_topic_state"]


    def _on_mqtt_subscription(self, topic, message, retained=None, qos=None, *args, **kwargs):
        message = message.decode("utf-8")     
        self._logger.info("mqtt: received a message for Topic {topic}. Message: {message}".format(**locals()))

        if message == self.config["mqtt_message_Off"] or message == self.config["mqtt_message_On"]:
            if message == self.config["mqtt_message_Off"] and self.isPSUOn:
                self._logger.debug("relaying OFF command to psucontrol")
                self.turn_psu_off()
            elif message == self.config["mqtt_message_On"] and not self.isPSUOn:
                self._logger.debug("relaying ON command to psucontrol")
                self.turn_psu_on()
            else:
                self._logger.debug("mqtt: mismatch between local and remote switch states, doing nothing.")
        else:
            self._logger.debug("mqtt: no supported message. Must be {} or {}".format(self.config["mqtt_message_On"],
                                                                                     self.config["mqtt_message_Off"]))

    def get_settings_defaults(self):
        return dict(
            mqtt_topic_state="homeassistant/switch/octoprint_PSUControl_switch/state",
            mqtt_topic_control="homeassistant/switch/octoprint_PSUControl_switch/set",
            mqtt_message_Off="OFF",
            mqtt_message_On="ON",
            ha_discovery_enable=False,
            ha_discovery_switch_name="PSU Control Switch",
            ha_discovery_device_name="PSU Control on Octoprint",
            ha_discovery_custom_NodeID=":-)",
            ha_discovery_optimistic=False,
            ha_discovery_merge_with_device=False,
            ha_discovery_minimal_device=False,
            ha_discovery_dont_create_device=False
        )

    def get_settings_version(self):
        return 2

    def on_settings_migrate(self, target, current):
        if current == 1:            
            self._settings.remove(["mqtt_topic_availability"])
            self._logger.info("Migrated to settings V2")

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    def on_event(self, event, payload):
        if event == Events.PLUGIN_PSUCONTROL_PSU_STATE_CHANGED:
            self._logger.debug("detected psu state change event: {}".format(payload))
            self.isPSUOn = payload["isPSUOn"]
            self.mqtt_publish(self.mqtt_topic_state, self.psu_state_to_message())
            self._logger.debug("updating switch state topic to {}".format(self.psu_state_to_message()))


    def on_plugin_disabled(self):
        self._logger.debug("removing discovery before disabling")
        self.remove_ha_discovery()

    def on_plugin_pending_uninstall(self):
        self._logger.debug("removing discovery before uninstalling")
        self.remove_ha_discovery()
    
    def on_settings_save(self, data):        
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.remove_ha_discovery()
        self.mqtt_unsubscribe(self._on_mqtt_subscription, self.mqtt_topic_control)
        self.reload_settings() # get new settings
        self.mqtt_subscribe(self.mqtt_topic_control, self._on_mqtt_subscription)       
        self.init_ha_discovery()
                
        self.isPSUOn = self.get_psu_state()
        self.mqtt_publish(self.mqtt_topic_state, self.psu_state_to_message())        

    def init_ha_discovery(self):
        if not self.config["ha_discovery_enable"]:
            return

        device = {
            "name": self.config["ha_discovery_device_name"],
            "ids":  self.ha_discovery_id,
            "sw_version": "Plugin version " + self._plugin_version,
            "manufacturer": self.device_manufacturer,
            "model": self._plugin_name
        }

        availability = {
            "topic": self.mqtt_topic_availability,
            "payload_available": self.available,
            "payload_not_available": self.unavailable
        }
        payload = {
            "device": device,
            "availability": availability,
            "name": self.config["ha_discovery_switch_name"],
            "unique_id": self.unique_id,
            "command_topic": self.mqtt_topic_control,
            "state_topic": self.mqtt_topic_state,
            "payload_on": self.config["mqtt_message_On"],
            "payload_off": self.config["mqtt_message_Off"],
            "optimistic": False
        }

        if self.config["ha_discovery_optimistic"]:
            payload["optimistic"] = True       
        if self.config["ha_discovery_merge_with_device"]:
             device = {"ids": self.config["ha_discovery_custom_NodeID"]}
        if self.config["ha_discovery_dont_create_device"]:
            del payload["device"]

        self._logger.debug("Enabling/Updating HA discovery feature")
        self.mqtt_publish(self.discoverytopic, payload)  # updating/creating discovery
        self._logger.debug("HA discovery payload was {}".format(payload))

    def remove_ha_discovery(self):    
        self.mqtt_publish(self.discoverytopic, {})
        self._logger.debug("Sending empty payload to delete discovery")

    def psu_state_to_message(self):
        if self.isPSUOn:
            return self.config["mqtt_message_On"]
        else:
            return self.config["mqtt_message_Off"]

    def get_update_information(self):
        return dict(
            mqtt_for_psucontrol=dict(
                displayName="MQTT exposure for PSU Control",
                displayVersion=self._plugin_version,
                type="github_release",
                current=self._plugin_version,
                user="oerkel47",
                repo="OctoPrint-MQTT-for-PSUcontrol",
                pip="https://github.com/oerkel47/OctoPrint-MQTT-for-PSUcontrol/archive/{target_version}.zip"
            )
        )


__plugin_name__ = "MQTT exposure for PSU Control"
__plugin_pythoncompat__ = ">=3,<4"


def __plugin_load__():
    global __plugin_implementation__
    global __plugin_hooks__

    __plugin_implementation__ = mqtt_for_psucontrol()
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
