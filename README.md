# OctoPrint-MQTT-for-PSUcontrol
This plugin interfaces between [PSU Control](https://github.com/kantlivelong/OctoPrint-PSUControl) plugin and [MQTT](https://github.com/OctoPrint/OctoPrint-MQTT) plugin and optionally adds support for [Home Assistant](https://www.home-assistant.io) discovery. 

## What it does
- Let's you control and monitor the switch that is configured in PSU Control via the MQTT protocol.
- Supports Home Assistant discovery to integrate everything without hassle.
- Supports adding the switch to existing device, for example [HomeAssistant discovery](https://github.com/cmroche/OctoPrint-HomeAssistant) plugin.

## What it does not
- This plugin is not meant to control any other switch except the one already configured in PSU Control.

## What you need
 - MQTT plugin for OctoPrint: **Be sure to use the newest version >= 0.8.10**
 - PSU Control plugin for OctoPrint
 - an MQTT broker of course
 - optional: HomeAssistant

But I guess you came here because you use those things anyway.


## Additional information
- Should also work if PSU Control subplugins are installed. I only did a short test for the Tasmota plugin though.
- If you run into issues, set plugin to debug and check log. There should be some good information for troubleshooting.
- I am an amateur programmer and this is my first Octoprint plugin. Please don't expect shiny code.


## Screenshot of Octoprint settings
![grafik](screenshot_settings.PNG)


## Screenshot of Home Assistant MQTT device
![grafik](screenshot_HomeAssistant.PNG)
