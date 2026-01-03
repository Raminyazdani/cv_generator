"""
Section Registry for CV Generator.

Provides a registry/adapter model for section rendering that allows:
- Registering custom section adapters
- Dynamic section discovery and rendering
- Plugin-based section extensions

The registry maintains backward compatibility with existing template-based sections.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from jinja2 import Environment

logger = logging.getLogger(__name__)


@runtime_checkable
class SectionAdapter(Protocol):
    """
    Protocol for section adapters.

    Adapters provide a consistent interface for rendering CV sections,
    allowing both built-in and plugin-provided sections to be handled uniformly.
    """

    @property
    def name(self) -> str:
        """Unique name of the section (e.g., 'education', 'experience')."""
        ...

    @property
    def template(self) -> str:
        """Template filename for this section (e.g., 'education.tex')."""
        ...

    def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate section data.

        Args:
            data: The CV data dictionary.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        ...

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize section data before rendering.

        Args:
            data: The CV data dictionary.

        Returns:
            Normalized data dictionary.
        """
        ...


class GenericSectionAdapter:
    """
    Generic adapter for template-based sections.

    This adapter works with existing templates without requiring custom logic.
    It provides a declarative way to define sections using configuration.
    """

    def __init__(
        self,
        name: str,
        template: str,
        data_key: Optional[str] = None,
        required: bool = False,
        validator: Optional[Callable[[Dict[str, Any]], List[str]]] = None,
        normalizer: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        """
        Initialize a generic section adapter.

        Args:
            name: Unique section name.
            template: Template filename (e.g., 'education.tex').
            data_key: Key in CV data for this section (defaults to name).
            required: Whether this section is required.
            validator: Optional custom validator function.
            normalizer: Optional custom normalizer function.
        """
        self._name = name
        self._template = template
        self._data_key = data_key or name
        self._required = required
        self._validator = validator
        self._normalizer = normalizer

    @property
    def name(self) -> str:
        """Get section name."""
        return self._name

    @property
    def template(self) -> str:
        """Get template filename."""
        return self._template

    @property
    def data_key(self) -> str:
        """Get the key used to access data for this section."""
        return self._data_key

    @property
    def required(self) -> bool:
        """Check if section is required."""
        return self._required

    def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate section data.

        Args:
            data: The CV data dictionary.

        Returns:
            List of validation error messages.
        """
        errors = []

        # Check if required section is present
        if self._required and self._data_key not in data:
            errors.append(f"Required section '{self._name}' is missing")

        # Run custom validator if provided
        if self._validator:
            custom_errors = self._validator(data)
            errors.extend(custom_errors)

        return errors

    def normalize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize section data.

        Args:
            data: The CV data dictionary.

        Returns:
            Normalized data dictionary.
        """
        if self._normalizer:
            return self._normalizer(data)
        return data

    def render(self, env: Environment, data: Dict[str, Any]) -> str:
        """
        Render the section using its template.

        Args:
            env: Jinja2 environment.
            data: The CV data dictionary.

        Returns:
            Rendered section content.
        """
        template = env.get_template(self.template)
        return template.render(data)

    def __repr__(self) -> str:
        return f"GenericSectionAdapter(name={self._name!r}, template={self._template!r})"


class SectionRegistry:
    """
    Registry for section adapters.

    Provides methods to register, retrieve, and list section adapters.
    The registry maintains insertion order for deterministic section ordering.
    """

    def __init__(self):
        """Initialize an empty section registry."""
        self._adapters: Dict[str, SectionAdapter] = {}
        self._order: List[str] = []

    def register(
        self,
        adapter: SectionAdapter,
        *,
        priority: Optional[int] = None,
    ) -> None:
        """
        Register a section adapter.

        Args:
            adapter: The section adapter to register.
            priority: Optional priority for ordering (lower = earlier).
                     If not specified, adapter is appended to the end.

        Raises:
            ValueError: If an adapter with the same name is already registered.
        """
        name = adapter.name

        if name in self._adapters:
            raise ValueError(f"Section adapter '{name}' is already registered")

        self._adapters[name] = adapter

        if priority is not None:
            # Insert at the specified priority position
            insert_pos = min(priority, len(self._order))
            self._order.insert(insert_pos, name)
        else:
            self._order.append(name)

        logger.debug(f"Registered section adapter: {name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a section adapter.

        Args:
            name: Name of the adapter to unregister.

        Returns:
            True if adapter was unregistered, False if not found.
        """
        if name in self._adapters:
            del self._adapters[name]
            self._order.remove(name)
            logger.debug(f"Unregistered section adapter: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[SectionAdapter]:
        """
        Get a section adapter by name.

        Args:
            name: Name of the adapter.

        Returns:
            The section adapter, or None if not found.
        """
        return self._adapters.get(name)

    def list(self) -> List[str]:
        """
        List all registered section names in order.

        Returns:
            List of section names in registration order.
        """
        return list(self._order)

    def list_adapters(self) -> List[SectionAdapter]:
        """
        List all registered adapters in order.

        Returns:
            List of adapters in registration order.
        """
        return [self._adapters[name] for name in self._order]

    def __len__(self) -> int:
        """Get the number of registered adapters."""
        return len(self._adapters)

    def __contains__(self, name: str) -> bool:
        """Check if an adapter is registered."""
        return name in self._adapters

    def __iter__(self):
        """Iterate over adapter names in order."""
        return iter(self._order)

    def clear(self) -> None:
        """Remove all registered adapters."""
        self._adapters.clear()
        self._order.clear()


# Default registry instance
_default_registry: Optional[SectionRegistry] = None


def get_default_registry() -> SectionRegistry:
    """
    Get the default section registry.

    Returns:
        The default SectionRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = create_default_registry()
    return _default_registry


def create_default_registry() -> SectionRegistry:
    """
    Create a registry with default section adapters.

    This registers adapters for all built-in CV sections,
    maintaining compatibility with existing templates.

    Returns:
        A new SectionRegistry with default adapters.
    """
    registry = SectionRegistry()

    # Define default sections in order
    # These match the existing template files in templates/
    default_sections = [
        ("header", "header.tex", "basics", True),
        ("education", "education.tex", "education", False),
        ("experience", "experience.tex", "experiences", False),
        ("skills", "skills.tex", "skills", False),
        ("projects", "projects.tex", "projects", False),
        ("publications", "publications.tex", "publications", False),
        ("certificates", "certificates.tex", "workshop_and_certifications", False),
        ("language", "language.tex", "languages", False),
        ("references", "references.tex", "references", False),
    ]

    for name, template, data_key, required in default_sections:
        adapter = GenericSectionAdapter(
            name=name,
            template=template,
            data_key=data_key,
            required=required,
        )
        registry.register(adapter)

    logger.debug(f"Created default registry with {len(registry)} sections")
    return registry


def reset_default_registry() -> None:
    """Reset the default registry to its initial state."""
    global _default_registry
    _default_registry = None


def register_section(
    name: str,
    template: str,
    data_key: Optional[str] = None,
    required: bool = False,
    priority: Optional[int] = None,
) -> GenericSectionAdapter:
    """
    Convenience function to register a new section in the default registry.

    Args:
        name: Unique section name.
        template: Template filename.
        data_key: Key in CV data (defaults to name).
        required: Whether section is required.
        priority: Optional priority for ordering.

    Returns:
        The created adapter.
    """
    adapter = GenericSectionAdapter(
        name=name,
        template=template,
        data_key=data_key,
        required=required,
    )
    get_default_registry().register(adapter, priority=priority)
    return adapter
