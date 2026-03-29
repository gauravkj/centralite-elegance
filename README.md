# Centralite Elegance

Home Assistant custom integration for Centralite Elegance, Elite, and Elegance XL lighting systems.

This integration connects to a Centralite panel over a serial connection and exposes supported loads to Home Assistant.

## Current status

### Tested
- Lights
- Fans

### Experimental
- Switches
- Scenes

Switches and scenes are included in the repository, but they should be considered experimental until they are fully tested in a real system.

## Features

- Local serial control
- Light entities for Centralite loads
- Fan entities for selected Centralite fan loads
- Optional switch entities
- Optional scene entities
- HACS compatible repository layout

## Repository layout

```text
custom_components/centralite/
