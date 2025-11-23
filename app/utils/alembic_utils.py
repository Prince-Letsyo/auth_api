from pathlib import Path
from alembic.config import Config
from alembic import command

# ----------------------------------------------------------------------
# 1. Resolve the *absolute* path to alembic.ini (project root)
# ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # ../../ from utils/
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
