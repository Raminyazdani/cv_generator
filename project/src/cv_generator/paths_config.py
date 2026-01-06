"""
Configuration-driven path management for cv_generator.

Provides flexible path resolution with the following precedence:
1. Explicit CLI flags (--cvs-dir, --pics-dir, --db-path, etc.)
2. Environment variables (CVGEN_DATA_DIR, CVGEN_CVS_DIR, etc.)
3. Configuration file (cv_generator.toml)
4. Legacy data/ directory (backward compatibility)
5. User home directory (~/.cvgen/)
6. Raise clear error if paths cannot be resolved
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Python 3.11+ has tomllib in stdlib, earlier versions need tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class PathConfig:
    """
    Centralized path configuration for all cv_generator data locations.

    Handles resolution precedence and provides clear error messages when
    required paths are missing.
    """

    def __init__(
        self,
        cvs_dir: Optional[Path] = None,
        pics_dir: Optional[Path] = None,
        db_path: Optional[Path] = None,
        templates_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        assets_dir: Optional[Path] = None,
        config_file: Optional[Path] = None,
        repo_root: Optional[Path] = None,
    ):
        """
        Initialize path configuration.

        Args:
            cvs_dir: Directory containing CV JSON files
            pics_dir: Directory containing profile pictures
            db_path: Path to SQLite database
            templates_dir: Directory containing LaTeX templates
            output_dir: Base directory for generated outputs
            assets_dir: Directory containing logos and other assets
            config_file: Path to cv_generator.toml config file
            repo_root: Repository root (for backward compatibility)
        """
        self._cvs_dir = cvs_dir
        self._pics_dir = pics_dir
        self._db_path = db_path
        self._templates_dir = templates_dir
        self._output_dir = output_dir
        self._assets_dir = assets_dir
        self._config_file = config_file
        self._repo_root = repo_root

        # Load configuration from file if provided
        self._config_data: Dict[str, Any] = {}
        if config_file and config_file.exists():
            self._load_config(config_file)

    def _load_config(self, config_file: Path):
        """Load paths from configuration file."""
        if tomllib is None:
            logger.warning("tomli/tomllib not available, skipping config file")
            return

        try:
            with open(config_file, "rb") as f:
                self._config_data = tomllib.load(f)
            logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            logger.error(f"Failed to load config file {config_file}: {e}")

    @property
    def cvs_dir(self) -> Path:
        """
        Get CVs directory with full precedence chain.

        Returns:
            Path: Resolved CVs directory

        Raises:
            FileNotFoundError: If CVs directory cannot be found
        """
        # 1. Explicit parameter
        if self._cvs_dir:
            logger.debug(f"Using explicit cvs_dir: {self._cvs_dir}")
            return self._cvs_dir

        # 2. Environment variable
        env_cvs_dir = os.getenv("CVGEN_CVS_DIR")
        if env_cvs_dir:
            path = Path(env_cvs_dir).expanduser()
            logger.debug(f"Using CVGEN_CVS_DIR: {path}")
            return path

        # 3. Environment variable for base data directory
        env_data_dir = os.getenv("CVGEN_DATA_DIR")
        if env_data_dir:
            path = Path(env_data_dir).expanduser() / "cvs"
            logger.debug(f"Using CVGEN_DATA_DIR/cvs: {path}")
            return path

        # 4. Configuration file
        if "paths" in self._config_data and "cvs_dir" in self._config_data["paths"]:
            path = Path(self._config_data["paths"]["cvs_dir"]).expanduser()
            logger.debug(f"Using config file cvs_dir: {path}")
            return path

        # 5. Legacy data/ directory (backward compatibility)
        if self._repo_root:
            legacy_path = self._repo_root / "data" / "cvs"
            if legacy_path.exists():
                logger.debug(f"Using legacy data/cvs: {legacy_path}")
                return legacy_path

        # 6. User home directory
        home_path = Path.home() / ".cvgen" / "cvs"
        if home_path.exists():
            logger.debug(f"Using user home directory: {home_path}")
            return home_path

        # 7. Current working directory fallback
        cwd_path = Path.cwd() / "cvs"
        if cwd_path.exists():
            logger.debug(f"Using current directory: {cwd_path}")
            return cwd_path

        # Cannot resolve - provide helpful error
        raise FileNotFoundError(
            "Cannot find CVs directory. Please specify using one of:\n"
            "  1. CLI flag: --cvs-dir /path/to/cvs\n"
            "  2. Environment: export CVGEN_CVS_DIR=/path/to/cvs\n"
            "  3. Config file: [paths] cvs_dir = '/path/to/cvs'\n"
            "  4. Create directory: mkdir -p ~/.cvgen/cvs\n"
            f"Searched locations:\n"
            f"  - CVGEN_CVS_DIR environment variable\n"
            f"  - CVGEN_DATA_DIR environment variable\n"
            f"  - Configuration file\n"
            + (f"  - Legacy: {self._repo_root / 'data' / 'cvs'}\n" if self._repo_root else "")
            + f"  - User home: {Path.home() / '.cvgen' / 'cvs'}\n"
            f"  - Current directory: {Path.cwd() / 'cvs'}"
        )

    @property
    def pics_dir(self) -> Path:
        """
        Get profile pictures directory with full precedence chain.

        Returns:
            Path: Resolved pics directory

        Raises:
            FileNotFoundError: If pics directory cannot be found
        """
        # 1. Explicit parameter
        if self._pics_dir:
            return self._pics_dir

        # 2. Environment variable
        env_pics_dir = os.getenv("CVGEN_PICS_DIR")
        if env_pics_dir:
            return Path(env_pics_dir).expanduser()

        # 3. Environment variable for base data directory
        env_data_dir = os.getenv("CVGEN_DATA_DIR")
        if env_data_dir:
            return Path(env_data_dir).expanduser() / "pics"

        # 4. Configuration file
        if "paths" in self._config_data and "pics_dir" in self._config_data["paths"]:
            return Path(self._config_data["paths"]["pics_dir"]).expanduser()

        # 5. Legacy data/ directory
        if self._repo_root:
            legacy_path = self._repo_root / "data" / "pics"
            if legacy_path.exists():
                return legacy_path

        # 6. User home directory
        home_path = Path.home() / ".cvgen" / "pics"
        if home_path.exists():
            return home_path

        # 7. Return default and warn (pictures are optional)
        default_path = Path.home() / ".cvgen" / "pics"
        logger.warning(
            f"Pictures directory not found. Using default: {default_path}\n"
            "Set CVGEN_PICS_DIR or create directory if needed."
        )
        return default_path

    @property
    def db_path(self) -> Path:
        """
        Get database path with full precedence chain.

        Returns:
            Path: Resolved database path
        """
        # 1. Explicit parameter
        if self._db_path:
            return self._db_path

        # 2. Environment variable
        env_db_path = os.getenv("CVGEN_DB_PATH")
        if env_db_path:
            return Path(env_db_path).expanduser()

        # 3. Environment variable for base data directory
        env_data_dir = os.getenv("CVGEN_DATA_DIR")
        if env_data_dir:
            return Path(env_data_dir).expanduser() / "db" / "cv.db"

        # 4. Configuration file
        if "paths" in self._config_data and "db_path" in self._config_data["paths"]:
            return Path(self._config_data["paths"]["db_path"]).expanduser()

        # 5. Legacy data/ directory
        if self._repo_root:
            legacy_path = self._repo_root / "data" / "db" / "cv.db"
            if legacy_path.exists():
                return legacy_path

        # 6. User home directory (default)
        return Path.home() / ".cvgen" / "db" / "cv.db"

    @property
    def templates_dir(self) -> Path:
        """
        Get templates directory with full precedence chain.

        Returns:
            Path: Resolved templates directory

        Raises:
            FileNotFoundError: If templates directory cannot be found
        """
        # 1. Explicit parameter
        if self._templates_dir:
            return self._templates_dir

        # 2. Environment variable
        env_templates_dir = os.getenv("CVGEN_TEMPLATES_DIR")
        if env_templates_dir:
            return Path(env_templates_dir).expanduser()

        # 3. Configuration file
        if "paths" in self._config_data and "templates_dir" in self._config_data["paths"]:
            return Path(self._config_data["paths"]["templates_dir"]).expanduser()

        # 4. Package templates (installed with package)
        # Look for templates in the package installation directory
        # Expected structure: site-packages/cv_generator/ with templates/ at repo root
        try:
            import cv_generator
            pkg_path = Path(cv_generator.__file__).parent
            # Try parent directories to find templates/
            for parent_level in range(3):  # Check up to 3 levels up
                potential_templates = pkg_path.parents[parent_level] / "templates"
                if potential_templates.exists():
                    return potential_templates
        except (ImportError, AttributeError, IndexError):
            pass

        # 5. Legacy templates/ directory
        if self._repo_root:
            legacy_path = self._repo_root / "templates"
            if legacy_path.exists():
                return legacy_path

        # 6. User home directory
        home_path = Path.home() / ".cvgen" / "templates"
        if home_path.exists():
            return home_path

        raise FileNotFoundError(
            "Cannot find LaTeX templates directory. Please specify using:\n"
            "  1. CLI flag: --templates-dir /path/to/templates\n"
            "  2. Environment: export CVGEN_TEMPLATES_DIR=/path/to/templates\n"
            "  3. Config file: [paths] templates_dir = '/path/to/templates'\n"
            "Templates are required for PDF generation."
        )

    @property
    def output_dir(self) -> Path:
        """
        Get output directory with precedence chain.

        Returns:
            Path: Resolved output directory (always returns a path, creates if needed)
        """
        # 1. Explicit parameter
        if self._output_dir:
            return self._output_dir

        # 2. Environment variable
        env_output_dir = os.getenv("CVGEN_OUTPUT_DIR")
        if env_output_dir:
            return Path(env_output_dir).expanduser()

        # 3. Configuration file
        if "paths" in self._config_data and "output_dir" in self._config_data["paths"]:
            return Path(self._config_data["paths"]["output_dir"]).expanduser()

        # 4. Current working directory (default)
        return Path.cwd() / "output"

    @property
    def assets_dir(self) -> Path:
        """
        Get assets directory (logos, etc.) with precedence chain.

        Returns:
            Path: Resolved assets directory
        """
        # 1. Explicit parameter
        if self._assets_dir:
            return self._assets_dir

        # 2. Environment variable
        env_assets_dir = os.getenv("CVGEN_ASSETS_DIR")
        if env_assets_dir:
            return Path(env_assets_dir).expanduser()

        # 3. Environment variable for base data directory
        env_data_dir = os.getenv("CVGEN_DATA_DIR")
        if env_data_dir:
            return Path(env_data_dir).expanduser() / "assets"

        # 4. Configuration file
        if "paths" in self._config_data and "assets_dir" in self._config_data["paths"]:
            return Path(self._config_data["paths"]["assets_dir"]).expanduser()

        # 5. Package assets (installed with package)
        # Look for assets in the package installation directory
        try:
            import cv_generator
            pkg_path = Path(cv_generator.__file__).parent
            # Try parent directories to find assets/
            for parent_level in range(3):  # Check up to 3 levels up
                potential_assets = pkg_path.parents[parent_level] / "assets"
                if potential_assets.exists():
                    return potential_assets
        except (ImportError, AttributeError, IndexError):
            pass

        # 6. Legacy assets/ directory
        if self._repo_root:
            legacy_path = self._repo_root / "assets"
            if legacy_path.exists():
                return legacy_path

        # 7. User home directory
        home_path = Path.home() / ".cvgen" / "assets"
        if home_path.exists():
            return home_path

        # 8. Return default (assets are optional)
        return Path.home() / ".cvgen" / "assets"

    def validate(self, require_cvs: bool = True, require_templates: bool = True):
        """
        Validate that all required paths exist.

        Args:
            require_cvs: If True, CVs directory must exist
            require_templates: If True, templates directory must exist

        Raises:
            FileNotFoundError: If required paths don't exist
        """
        errors = []

        if require_cvs:
            try:
                cvs_dir = self.cvs_dir
                if not cvs_dir.exists():
                    errors.append(f"CVs directory does not exist: {cvs_dir}")
            except FileNotFoundError as e:
                errors.append(str(e))

        if require_templates:
            try:
                templates_dir = self.templates_dir
                if not templates_dir.exists():
                    errors.append(f"Templates directory does not exist: {templates_dir}")
            except FileNotFoundError as e:
                errors.append(str(e))

        if errors:
            raise FileNotFoundError("\n".join(errors))

    def create_user_directories(self):
        """
        Create default user directories in ~/.cvgen/

        Useful for initial setup.
        """
        base_dir = Path.home() / ".cvgen"
        dirs_to_create = [
            base_dir / "cvs",
            base_dir / "pics",
            base_dir / "db",
            base_dir / "assets",
            base_dir / "templates",
        ]

        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")

        logger.info(f"User directories created in {base_dir}")

    def __repr__(self):
        """String representation for debugging."""
        try:
            return (
                f"PathConfig(\n"
                f"  cvs_dir={self.cvs_dir},\n"
                f"  pics_dir={self.pics_dir},\n"
                f"  db_path={self.db_path},\n"
                f"  templates_dir={self.templates_dir},\n"
                f"  output_dir={self.output_dir},\n"
                f"  assets_dir={self.assets_dir}\n"
                f")"
            )
        except FileNotFoundError:
            return "PathConfig(unresolved)"


def create_path_config_from_cli(args) -> PathConfig:
    """
    Create PathConfig from parsed CLI arguments.

    Args:
        args: argparse.Namespace with CLI arguments

    Returns:
        PathConfig: Configured path resolver
    """
    # Get config file path
    config_file = None
    if hasattr(args, "config_file") and args.config_file:
        config_file = Path(args.config_file)
    elif Path("cv_generator.toml").exists():
        config_file = Path("cv_generator.toml")

    # Try to determine repo root for backward compatibility
    repo_root = None
    if hasattr(args, "repo_root") and args.repo_root:
        repo_root = Path(args.repo_root)
    else:
        # Try to auto-detect
        from cv_generator.paths import get_repo_root

        try:
            repo_root = get_repo_root()
        except Exception:
            pass  # No repo root available

    # Extract explicit paths from CLI args
    return PathConfig(
        cvs_dir=Path(args.cvs_dir) if hasattr(args, "cvs_dir") and args.cvs_dir else None,
        pics_dir=Path(args.pics_dir) if hasattr(args, "pics_dir") and args.pics_dir else None,
        db_path=Path(args.db_path) if hasattr(args, "db_path") and args.db_path else None,
        templates_dir=Path(args.templates_dir) if hasattr(args, "templates_dir") and args.templates_dir else None,
        output_dir=Path(args.output_dir) if hasattr(args, "output_dir") and args.output_dir else None,
        assets_dir=Path(args.assets_dir) if hasattr(args, "assets_dir") and args.assets_dir else None,
        config_file=config_file,
        repo_root=repo_root,
    )
