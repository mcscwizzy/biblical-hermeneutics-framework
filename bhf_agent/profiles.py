"""Profile loading for committed BHF prompt profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union


class ProfileError(ValueError):
    """Raised when a requested BHF profile cannot be loaded."""


@dataclass(frozen=True)
class Profile:
    name: str
    content: str
    path: Path


class ProfileLoader:
    def __init__(self, profiles_dir: Optional[Union[str, Path]] = None) -> None:
        self.profiles_dir = Path(profiles_dir) if profiles_dir else _default_profiles_dir()

    def load(self, profile_name: str) -> Profile:
        if not profile_name or "/" in profile_name or "\\" in profile_name:
            raise ProfileError("profile name must be a simple profile id")
        path = self.profiles_dir / f"{profile_name}.md"
        if not path.exists():
            known = ", ".join(self.available_profiles()) or "(none found)"
            raise ProfileError(f"profile '{profile_name}' not found. Available: {known}")
        return Profile(
            name=profile_name,
            content=path.read_text(encoding="utf-8"),
            path=path,
        )

    def available_profiles(self) -> list[str]:
        if not self.profiles_dir.exists():
            return []
        return sorted(path.stem for path in self.profiles_dir.glob("*.md"))


def _default_profiles_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "profiles"
