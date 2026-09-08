from dataclasses import dataclass, field
from typing import Any


@dataclass
class Packet:
    type: str  # "CLIENT" | "SERVER"
    version: str
    cwd: str
    env: dict[str, str]

    # Standard message dict:
    # "prompt": str   -> prompt to model  (server/daemon)

    message: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "version": self.version,
            "cwd": self.cwd,
            "env": self.env,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Packet:
        return cls(
            type=data["type"],
            version=data.get("version", ""),
            cwd=data.get("cwd", ""),
            env=data.get("env", {}),
            message=data.get("message", {}),
        )

