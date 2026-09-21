from __future__ import annotations

import base64
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def encode(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    request = {
        "displayName": "IndustrialIoT_Eventstream",
        "description": "Validated industrial IoT events from the simulator routed to Eventhouse and Fabric Activator.",
        "type": "Eventstream",
        "definition": {
            "parts": [
                {"path": "eventstream.json", "payload": encode(ROOT / "eventstream.json"), "payloadType": "InlineBase64"},
                {"path": "eventstreamProperties.json", "payload": encode(ROOT / "eventstreamProperties.json"), "payloadType": "InlineBase64"},
                {"path": ".platform", "payload": encode(ROOT / ".platform"), "payloadType": "InlineBase64"},
            ]
        },
    }
    output = ROOT / "create_item.request.rendered.json"
    output.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()