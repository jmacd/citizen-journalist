"""Load repository skills as hashed, versioned procedural policy."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class SkillPolicy:
    name: str
    path: Path
    content: str
    sha256: str


def load_skills(repo_root: Path) -> dict[str, SkillPolicy]:
    skill_root = repo_root / ".github" / "skills"
    policies: dict[str, SkillPolicy] = {}
    for path in sorted(skill_root.glob("*/SKILL.md")):
        content = path.read_text(encoding="utf-8")
        name = path.parent.name
        policies[name] = SkillPolicy(
            name=name,
            path=path,
            content=content,
            sha256=sha256(content.encode("utf-8")).hexdigest(),
        )
    return policies
