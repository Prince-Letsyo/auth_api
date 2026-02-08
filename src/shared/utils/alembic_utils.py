from pathlib import Path

from alembic import command
from alembic.config import Config

# ----------------------------------------------------------------------
# 1. Resolve the *absolute* path to alembic.ini (project root)
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # ../../../ from shared/utils/
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


# ----------------------------------------------------------------------
# 2. Optional: inject the *sync* DB URL at runtime
# ----------------------------------------------------------------------
def _make_alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    return cfg


def upgrade_database() -> None:
    """
    Run `alembic upgrade head`.
    """
    cfg = _make_alembic_config()
    command.upgrade(cfg, "head")


def downgrade_database(revision: str = "-1") -> None:
    cfg = _make_alembic_config()
    command.downgrade(cfg, revision)


def is_valid_url(url: str) -> bool:
    """Simple check if a string is a valid URL."""
    return url.startswith(("http://", "https://"))
