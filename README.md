# Centralite Elegance

Home Assistant custom integration for Centralite Elegance, Elite, and Elegance XL lighting systems.

This integration connects to a Centralite panel over a serial connection and exposes supported loads as Home Assistant entities.

## Current status

### Tested
- Lights
- Fans
- HACS custom repository installation
- Config flow setup from Home Assistant UI

### Experimental
- Switches
- Scenes

Switches and scenes are included in the repository but should be treated as experimental until they are validated more broadly.

## Features

- Local serial control
- Light entities for Centralite loads
- Fan entities for selected Centralite fan loads
- Optional switch entities
- Optional scene entities
- Home Assistant config flow support
- HACS compatible repository layout
- Optional local naming override file

## Repository layout

`custom_components/centralite/`

## Installation

### Option 1. HACS custom repository

1. Open HACS in Home Assistant
2. Open the menu
3. Select **Custom repositories**
4. Add this repository URL:  
   `https://github.com/gauravkj/centralite-elegance`
5. Select category: **Integration**
6. Install **Centralite Elegance**
7. Restart Home Assistant

### Option 2. Manual installation

1. Copy the `custom_components/centralite` folder into your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

This integration uses Home Assistant config flow.

Go to:

**Settings → Devices & Services → Add Integration**

Then search for:

**Centralite**

You will be prompted for:
- Serial port
- Whether to include switches
- Whether to include scenes

### Recommended setup

If you have not tested switches and scenes yet:
- leave `include_switches` disabled
- leave `include_scenes` disabled

## Serial connection

Typical serial settings used by this integration:

- Baud rate: `19200`
- Parity: `None`
- Stop bits: `1`

Example serial path on Home Assistant OS:

`/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_D_00011412-if00-port0`

## Supported entity types

### Lights

Most Centralite loads are exposed as Home Assistant light entities.

### Fans

Selected fan loads are exposed as Home Assistant fan entities.

Current fan load mapping in this integration:

- `50`
- `51`
- `52`
- `54`
- `55`
- `56`
- `59`
- `60`

### Switches

Switch support exists but is still experimental.

### Scenes

Scene support exists but is still experimental.

## Optional local naming overrides

This repository is intended to be reusable for different Centralite installations.

Because load names vary from house to house, the integration supports an optional local naming file on your Home Assistant system.

Create this file:

`/config/centralite_names.json`

Do not place it inside `custom_components`.

### Example


So that section becomes:

```md
### Example

```json
{
  "loads": {
    "1": "Kitchen Table",
    "2": "Laundry Lights",
    "3": "Kitchen Island"
  },
  "fans": {
    "50": "Master Bedroom Fan",
    "51": "Family Room Fan"
  }
}


### Behavior

- If `/config/centralite_names.json` exists, the integration uses those names
- If the file does not exist, the integration falls back to generic names such as:
  - `L001`
  - `L002`
  - `L050 Fan`

## Notes

- This is a custom integration and is not part of Home Assistant Core
- This integration is intended for local serial based Centralite systems
- Load numbering and room naming will vary by installation
- If a load is physically used for a fan or outlet, verify that your naming and entity type choices match your installation
- For public reuse, the repository code should remain generic, and installation specific naming should live in `/config/centralite_names.json`

## Known limitations

- Switches are not fully validated
- Scenes are not fully validated
- Entity naming depends on the Centralite load mapping and optional local naming file
- Fan support depends on known fan capable loads being mapped correctly

## Troubleshooting

### The integration does not appear in Add Integration

Check that:
- `manifest.json` includes `"config_flow": true`
- `config_flow.py` exists in `custom_components/centralite`
- Home Assistant has been restarted after installation

### I see duplicate or unavailable entities

This can happen when migrating from an older YAML based version or from a prior custom integration version with different entity identities.

Recommended approach:
- confirm the new working entities first
- remove stale unavailable duplicates
- avoid repeated registry surgery once the integration is stable

### Names are generic like `L001`

That means the integration did not find a local naming override file.

Create:

`/config/centralite_names.json`

and restart Home Assistant.

## Development notes

This repository has been modernized toward:
- config entries
- config flow based setup
- HACS based distribution
- stable numeric unique IDs

Future improvements may include:
- cleaner switch support
- cleaner scene support
- richer options flow
- more user friendly translations

## Issues

If you find a problem, please open an issue here:

`https://github.com/gauravkj/centralite-elegance/issues`

## License

See the repository license file.
