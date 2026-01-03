"""
Configuration file support for CV Generator.

Provides:
- Config dataclass for holding configuration values
- TOML config file loading (cv_generator.toml)
- Precedence: CLI > config file > defaults
- Profile state management (.cvgen/state.json)
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Python 3.11+ has tomllib in stdlib, earlier versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]

from .paths import get_repo_root

logger = logging.getLogger(__name__)

# Default config file name
DEFAULT_CONFIG_NAME = "cv_generator.toml"

# State directory (outside data/)
STATE_DIR_NAME = ".cvgen"
STATE_FILE_NAME = "state.json"


@dataclass
class ProjectConfig:
    """Project-level configuration."""

    name: str = ""
    default_lang: str = "en"
    variants: List[str] = field(default_factory=list)


@dataclass
class PathsConfig:
    """Path configuration."""

    cvs: Optional[str] = None
    templates: Optional[str] = None
    output: Optional[str] = None
    db: Optional[str] = None


@dataclass
class BuildConfig:
    """Build configuration."""

    latex_engine: str = "xelatex"
    keep_latex: bool = False
    dry_run: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "WARNING"
    log_file: Optional[str] = None


@dataclass
class Config:
    """Complete configuration for CV Generator."""

    project: ProjectConfig = field(default_factory=ProjectConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    build: BuildConfig = field(default_factory=BuildConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    config_path: Optional[Path] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: Optional[Path] = None) -> "Config":
        """Create Config from a dictionary (parsed TOML)."""
        project_data = data.get("project", {})
        paths_data = data.get("paths", {})
        build_data = data.get("build", {})
        logging_data = data.get("logging", {})

        return cls(
            project=ProjectConfig(
                name=project_data.get("name", ""),
                default_lang=project_data.get("default_lang", "en"),
                variants=project_data.get("variants", []),
            ),
            paths=PathsConfig(
                cvs=paths_data.get("cvs"),
                templates=paths_data.get("templates"),
                output=paths_data.get("output"),
                db=paths_data.get("db"),
            ),
            build=BuildConfig(
                latex_engine=build_data.get("latex_engine", "xelatex"),
                keep_latex=build_data.get("keep_latex", False),
                dry_run=build_data.get("dry_run", False),
            ),
            logging=LoggingConfig(
                level=logging_data.get("level", "WARNING"),
                log_file=logging_data.get("log_file"),
            ),
            config_path=config_path,
        )


class ConfigError(Exception):
    """Error loading or parsing configuration."""

    pass


def find_config_file(config_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the configuration file.

    Search order:
    1. Explicit path if provided
    2. cv_generator.toml in current directory
    3. cv_generator.toml in repository root

    Args:
        config_path: Explicit path to config file.

    Returns:
        Path to config file, or None if not found.
    """
    if config_path is not None:
        if config_path.exists():
            return config_path
        raise ConfigError(f"Config file not found: {config_path}")

    # Check current directory
    cwd_config = Path.cwd() / DEFAULT_CONFIG_NAME
    if cwd_config.exists():
        return cwd_config

    # Check repository root
    repo_root = get_repo_root()
    root_config = repo_root / DEFAULT_CONFIG_NAME
    if root_config.exists():
        return root_config

    return None


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from a TOML file.

    If no config file is found, returns default configuration.

    Args:
        config_path: Optional explicit path to config file.

    Returns:
        Config object with loaded or default values.

    Raises:
        ConfigError: If config file exists but cannot be parsed.
    """
    config_file = find_config_file(config_path)

    if config_file is None:
        logger.debug("No config file found, using defaults")
        return Config()

    if tomllib is None:
        logger.warning(
            "TOML parsing not available. Install 'tomli' package for Python < 3.11"
        )
        return Config()

    logger.debug(f"Loading config from: {config_file}")

    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Invalid TOML in {config_file}: {e}")
    except OSError as e:
        raise ConfigError(f"Cannot read config file {config_file}: {e}")

    config = Config.from_dict(data, config_path=config_file)
    logger.info(f"Loaded config from: {config_file}")
    return config


# ============================================================================
# Profile State Management
# ============================================================================


def get_state_dir() -> Path:
    """Get the state directory path (.cvgen/)."""
    return get_repo_root() / STATE_DIR_NAME


def get_state_file() -> Path:
    """Get the state file path (.cvgen/state.json)."""
    return get_state_dir() / STATE_FILE_NAME


def load_state() -> Dict[str, Any]:
    """
    Load the current state from .cvgen/state.json.

    Returns:
        State dictionary, or empty dict if no state file exists.
    """
    state_file = get_state_file()

    if not state_file.exists():
        return {}

    try:
        with open(state_file, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load state file: {e}")
        return {}


def save_state(state: Dict[str, Any]) -> None:
    """
    Save state to .cvgen/state.json.

    Args:
        state: State dictionary to save.
    """
    state_dir = get_state_dir()
    state_file = get_state_file()

    # Create directory if needed
    state_dir.mkdir(parents=True, exist_ok=True)

    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.debug(f"Saved state to: {state_file}")
    except OSError as e:
        logger.error(f"Could not save state file: {e}")


def get_current_profile() -> Optional[str]:
    """
    Get the currently selected profile from state.

    Returns:
        Profile name, or None if not set.
    """
    state = load_state()
    return state.get("current_profile")


def set_current_profile(profile: str) -> None:
    """
    Set the current profile in state.

    Args:
        profile: Profile name to set as current.
    """
    state = load_state()
    state["current_profile"] = profile
    save_state(state)
    logger.info(f"Set current profile to: {profile}")


def clear_current_profile() -> None:
    """Clear the current profile from state."""
    state = load_state()
    if "current_profile" in state:
        del state["current_profile"]
        save_state(state)
        logger.info("Cleared current profile")


# ============================================================================
# Profile Discovery
# ============================================================================


def list_profiles(cvs_dir: Optional[Path] = None) -> List[str]:
    """
    List available profiles from the CVs directory.

    Profiles are identified by the base name of JSON files in data/cvs/.

    Args:
        cvs_dir: Path to CVs directory. Defaults to data/cvs.

    Returns:
        List of unique profile names.
    """
    from .io import parse_cv_filename
    from .paths import get_default_cvs_path

    if cvs_dir is None:
        cvs_dir = get_default_cvs_path()

    if not cvs_dir.exists():
        return []

    profiles = set()
    for filepath in cvs_dir.glob("*.json"):
        base_name, _ = parse_cv_filename(filepath.name)
        profiles.add(base_name)

    return sorted(profiles)
