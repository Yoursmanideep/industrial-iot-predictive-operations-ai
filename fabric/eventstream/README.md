# Fabric Eventstream

Stage 3.15 uses a Custom Endpoint source for live simulator events and routes the default stream to Eventhouse and Fabric Activator.

## Definition files

- `eventstream.json` — topology payload with sources, destinations, operators and streams
- `eventstreamProperties.json` — throughput/retention properties
- `.platform` — Fabric metadata template
- `create_item.request.json` — API create-item request with Base64 placeholders

## Runtime topology

Simulator Custom Endpoint
        ↓
IndustrialIoT_Eventstream
    ┌────┴────┐
    ↓         ↓
Eventhouse  Activator
    ↓         ↓
    KQL     Power Automate

## Authentication

The repository does not contain endpoint keys.

Use Microsoft Entra ID / managed identity where the deployment supports it. A SAS connection string may be injected at runtime through `FABRIC_EVENTSTREAM_CONNECTION_STRING` for the simulator publisher, but never committed to Git.

## Eventstream API

The current Fabric REST definition models Eventstream as a graph of sources, destinations, operators and streams.

The included JSON is intentionally environment-parameterized. Workspace/item IDs and the generated Eventstream connection details are deployment-time values.

## Operational rule

Publish the Eventstream and verify the live preview before enabling Activator rules. Microsoft recommends validating the live event schema before creating Activator rules.