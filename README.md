# OctoPrint-MQTT-for-PSUcontrol
This plugin interfaces between [PSUControl](https://github.com/kantlivelong/OctoPrint-PSUControl) plugin and [MQTT](https://github.com/OctoPrint/OctoPrint-MQTT) plugin and optionally adds support for [HomeAssistant](https://www.home-assistant.io) discovery. 

## What it does
- Let's you control and monitor the switch that is configured in PSUControl via the MQTT protocol.
- Supports HomeAssistant discovery to integrate everything without hassle.

## What it does not
- This plugin is not meant to control any other switch except the one configured in PSUControl.

## What you need
 - MQTT plugin for OctoPrint: **Be sure to use the newest version >= 0.8.10**
 - PSUControl plugin for OctoPrint
 - an MQTT broker of course
 - optional: HomeAssistant

But I guess you came here because you use those things anyway.


## Additional information
- Should also work if PSUControl subplugins are installed. I only did a short test for the Tasmota plugin though.
- If you run into issues, set plugin to debug and check log. There should be some good information for troubleshooting.
### Disclaimer
I am an amateur programmer and this is my first Octoprint plugin. Please don't expect shiny code.

## Screenshot Octoprint settings
![grafik](https://github.com/oerkel47/OctoPrint-MQTT-for-PSUcontrol/blob/main/screenshot_settings.PNG)

## Screenshot Home Assistant MQTT device
![grafik](https://github.com/oerkel47/OctoPrint-MQTT-for-PSUcontrol/blob/main/screenshot_HomeAssistant.PNG)
