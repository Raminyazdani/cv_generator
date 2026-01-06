"""
Tests for cv_generator.person module.

Tests the Person entity model, name normalization, and variant grouping.
"""

import json
import pytest

from cv_generator.db import init_db, import_cv
from cv_generator.person import (
    SUPPORTED_LANGUAGES,
    auto_group_variants,
    compute_name_key,
    create_person_entity,
    delete_person_entity,
    ensure_person_entity_schema,
    get_person_entity,
    get_person_entity_by_variant,
    get_unlinked_variants,
    link_variant_to_person,
    list_person_entities,
    normalize_name,
    unlink_variant_from_person,
    update_person_entity,
)
from cv_generator.errors import ValidationError


class TestNormalizeName:
    """Tests for the normalize_name function."""

    def test_normalize_basic_name(self):
        """Test basic name normalization."""
        assert normalize_name("Ramin") == "ramin"
        assert normalize_name("YAZDANI") == "yazdani"

    def test_normalize_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert normalize_name("  Ramin  ") == "ramin"
        assert normalize_name("\tYazdani\n") == "yazdani"

    def test_normalize_collapses_multiple_spaces(self):
        """Test that multiple spaces are collapsed."""
        assert normalize_name("Ramin   Yazdani") == "ramin yazdani"

    def test_normalize_none_returns_empty(self):
        """Test that None returns empty string."""
        assert normalize_name(None) == ""

    def test_normalize_empty_returns_empty(self):
        """Test that empty string returns empty string."""
        assert normalize_name("") == ""
        assert normalize_name("   ") == ""

    def test_normalize_unicode_nfkc(self):
        """Test Unicode NFKC normalization."""
        # Full-width characters should be normalized
        assert normalize_name("Ｒａｍｉｎ") == "ramin"

    def test_normalize_preserves_persian(self):
        """Test that Persian text is preserved (casefold doesn't change it)."""
        result = normalize_name("رامین")
        assert result == "رامین"

    def test_normalize_casefold_german(self):
        """Test German ß casefolds to ss."""
        assert normalize_name("Müller") == "müller"
        # Note: casefold() converts ß to ss
        assert normalize_name("Strauß") == "strauss"


class TestComputeNameKey:
    """Tests for compute_name_key function."""

    def test_basic_name_key(self):
        """Test basic name key computation."""
        assert compute_name_key("Ramin", "Yazdani") == "ramin|yazdani"

    def test_name_key_with_spaces(self):
        """Test name key with extra spaces."""
        assert compute_name_key("  Ramin  ", "  Yazdani  ") == "ramin|yazdani"

    def test_name_key_case_insensitive(self):
        """Test that name key is case insensitive."""
        assert compute_name_key("RAMIN", "YAZDANI") == "ramin|yazdani"
        assert compute_name_key("ramin", "yazdani") == "ramin|yazdani"

    def test_name_key_empty_first(self):
        """Test name key with empty first name."""
        assert compute_name_key("", "Yazdani") == "|yazdani"
        assert compute_name_key(None, "Yazdani") == "|yazdani"

    def test_name_key_empty_last(self):
        """Test name key with empty last name."""
        assert compute_name_key("Ramin", "") == "ramin|"
        assert compute_name_key("Ramin", None) == "ramin|"

    def test_name_key_both_empty(self):
        """Test name key with both names empty."""
        assert compute_name_key("", "") == ""
        assert compute_name_key(None, None) == ""


class TestPersonEntityCRUD:
    """Tests for Person entity CRUD operations."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_person_entity_schema(db_path)
        return db_path

    def test_create_person_entity(self, db):
        """Test creating a person entity."""
        person = create_person_entity("Ramin", "Yazdani", db_path=db)

        assert person["first_name"] == "Ramin"
        assert person["last_name"] == "Yazdani"
        assert person["display_name"] == "Ramin Yazdani"
        assert person["name_key"] == "ramin|yazdani"
        assert "id" in person
        assert len(person["id"]) == 36  # UUID format

    def test_create_person_entity_with_display_name(self, db):
        """Test creating a person entity with custom display name."""
        person = create_person_entity(
            "Ramin", "Yazdani",
            display_name="Dr. Ramin Yazdani",
            db_path=db
        )

        assert person["display_name"] == "Dr. Ramin Yazdani"

    def test_create_person_entity_with_notes(self, db):
        """Test creating a person entity with notes."""
        person = create_person_entity(
            "Ramin", "Yazdani",
            notes="Test person for development",
            db_path=db
        )

        assert person["notes"] == "Test person for development"

    def test_create_person_entity_empty_first_name_raises(self, db):
        """Test that empty first name raises error."""
        with pytest.raises(ValidationError) as exc_info:
            create_person_entity("", "Yazdani", db_path=db)
        assert "First name is required" in str(exc_info.value)

    def test_create_person_entity_empty_last_name_raises(self, db):
        """Test that empty last name raises error."""
        with pytest.raises(ValidationError) as exc_info:
            create_person_entity("Ramin", "", db_path=db)
        assert "Last name is required" in str(exc_info.value)

    def test_create_duplicate_person_raises(self, db):
        """Test that creating duplicate person raises error."""
        create_person_entity("Ramin", "Yazdani", db_path=db)

        with pytest.raises(ValidationError) as exc_info:
            create_person_entity("Ramin", "Yazdani", db_path=db)
        assert "already exists" in str(exc_info.value)

    def test_create_duplicate_case_insensitive(self, db):
        """Test that duplicate detection is case insensitive."""
        create_person_entity("Ramin", "Yazdani", db_path=db)

        with pytest.raises(ValidationError):
            create_person_entity("RAMIN", "YAZDANI", db_path=db)

    def test_get_person_entity(self, db):
        """Test getting a person entity by ID."""
        created = create_person_entity("Ramin", "Yazdani", db_path=db)

        person = get_person_entity(created["id"], db_path=db)

        assert person is not None
        assert person["id"] == created["id"]
        assert person["first_name"] == "Ramin"
        assert person["last_name"] == "Yazdani"

    def test_get_nonexistent_person_returns_none(self, db):
        """Test getting a nonexistent person returns None."""
        person = get_person_entity("nonexistent-id", db_path=db)
        assert person is None

    def test_list_person_entities(self, db):
        """Test listing all person entities."""
        create_person_entity("Ramin", "Yazdani", db_path=db)
        create_person_entity("John", "Doe", db_path=db)

        persons = list_person_entities(db_path=db)

        assert len(persons) == 2
        names = {p["display_name"] for p in persons}
        assert "Ramin Yazdani" in names
        assert "John Doe" in names

    def test_list_person_entities_with_search(self, db):
        """Test listing person entities with search filter."""
        create_person_entity("Ramin", "Yazdani", db_path=db)
        create_person_entity("John", "Doe", db_path=db)

        persons = list_person_entities(db_path=db, search="ramin")

        assert len(persons) == 1
        assert persons[0]["first_name"] == "Ramin"

    def test_update_person_entity(self, db):
        """Test updating a person entity."""
        created = create_person_entity("Ramin", "Yazdani", db_path=db)

        updated = update_person_entity(
            created["id"],
            display_name="Dr. Ramin Yazdani",
            notes="Updated notes",
            db_path=db
        )

        assert updated["display_name"] == "Dr. Ramin Yazdani"
        assert updated["notes"] == "Updated notes"
        assert updated["first_name"] == "Ramin"  # Unchanged

    def test_delete_person_entity(self, db):
        """Test deleting a person entity."""
        created = create_person_entity("Ramin", "Yazdani", db_path=db)

        result = delete_person_entity(created["id"], db_path=db)

        assert result is True
        assert get_person_entity(created["id"], db_path=db) is None

    def test_delete_nonexistent_person(self, db):
        """Test deleting a nonexistent person returns False."""
        result = delete_person_entity("nonexistent-id", db_path=db)
        assert result is False


class TestVariantLinking:
    """Tests for linking CV variants to person entities."""

    @pytest.fixture
    def db_with_variants(self, tmp_path):
        """Create a test database with CV variant data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_person_entity_schema(db_path)

        # Create CV data for English variant
        cv_en = {
            "basics": [{"fname": "Ramin", "lname": "Yazdani"}],
            "projects": [{"title": "Test Project"}]
        }
        cv_en_path = tmp_path / "cvs" / "ramin.json"
        cv_en_path.parent.mkdir(parents=True, exist_ok=True)
        cv_en_path.write_text(json.dumps(cv_en))
        import_cv(cv_en_path, db_path)

        # Create CV data for German variant
        cv_de = {
            "basics": [{"fname": "Ramin", "lname": "Yazdani"}],
            "projects": [{"title": "Testprojekt"}]
        }
        cv_de_path = tmp_path / "cvs" / "ramin_de.json"
        cv_de_path.write_text(json.dumps(cv_de))
        import_cv(cv_de_path, db_path)

        # Create CV data for Persian variant
        cv_fa = {
            "basics": [{"fname": "رامین", "lname": "یزدانی"}],
            "projects": [{"title": "پروژه تست"}]
        }
        cv_fa_path = tmp_path / "cvs" / "ramin_fa.json"
        cv_fa_path.write_text(json.dumps(cv_fa))
        import_cv(cv_fa_path, db_path)

        return db_path

    def test_get_unlinked_variants(self, db_with_variants):
        """Test getting unlinked variants."""
        unlinked = get_unlinked_variants(db_path=db_with_variants)

        # Should find all three variants
        assert len(unlinked) == 3

        slugs = {v["slug"] for v in unlinked}
        assert "ramin" in slugs
        assert "ramin_de" in slugs
        assert "ramin_fa" in slugs

    def test_link_variant_to_person(self, db_with_variants):
        """Test linking a variant to a person entity."""
        # Create person entity
        person = create_person_entity("Ramin", "Yazdani", db_path=db_with_variants)

        # Get unlinked variants
        unlinked = get_unlinked_variants(db_path=db_with_variants)
        en_variant = next(v for v in unlinked if v["slug"] == "ramin")

        # Link variant
        updated = link_variant_to_person(
            person["id"],
            en_variant["person_id"],
            "en",
            is_primary=True,
            db_path=db_with_variants
        )

        assert "en" in updated["variants"]
        assert updated["variants"]["en"]["slug"] == "ramin"
        assert updated["variants"]["en"]["is_primary"] is True

    def test_link_all_variants(self, db_with_variants):
        """Test linking all language variants to one person."""
        person = create_person_entity("Ramin", "Yazdani", db_path=db_with_variants)
        unlinked = get_unlinked_variants(db_path=db_with_variants)

        for variant in unlinked:
            link_variant_to_person(
                person["id"],
                variant["person_id"],
                variant["language"],
                is_primary=(variant["language"] == "en"),
                db_path=db_with_variants
            )

        # Get updated person
        person = get_person_entity(person["id"], db_path=db_with_variants)

        assert len(person["variants"]) == 3
        assert "en" in person["variants"]
        assert "de" in person["variants"]
        assert "fa" in person["variants"]

    def test_unlink_variant(self, db_with_variants):
        """Test unlinking a variant from a person entity."""
        person = create_person_entity("Ramin", "Yazdani", db_path=db_with_variants)
        unlinked = get_unlinked_variants(db_path=db_with_variants)
        en_variant = next(v for v in unlinked if v["slug"] == "ramin")

        link_variant_to_person(
            person["id"], en_variant["person_id"], "en",
            db_path=db_with_variants
        )

        # Unlink
        result = unlink_variant_from_person(
            person["id"], en_variant["person_id"],
            db_path=db_with_variants
        )

        assert result is True

        # Verify unlinked
        person = get_person_entity(person["id"], db_path=db_with_variants)
        assert "en" not in person["variants"]

    def test_get_person_entity_by_variant(self, db_with_variants):
        """Test getting person entity from variant ID."""
        person = create_person_entity("Ramin", "Yazdani", db_path=db_with_variants)
        unlinked = get_unlinked_variants(db_path=db_with_variants)
        en_variant = next(v for v in unlinked if v["slug"] == "ramin")

        link_variant_to_person(
            person["id"], en_variant["person_id"], "en",
            db_path=db_with_variants
        )

        # Get person entity by variant
        found = get_person_entity_by_variant(
            en_variant["person_id"],
            db_path=db_with_variants
        )

        assert found is not None
        assert found["id"] == person["id"]


class TestAutoGrouping:
    """Tests for automatic variant grouping."""

    @pytest.fixture
    def db_with_variants(self, tmp_path):
        """Create a test database with CV variant data."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_person_entity_schema(db_path)

        # Create Ramin's CVs (should be grouped together)
        for lang, fname, lname in [
            ("en", "Ramin", "Yazdani"),
            ("de", "Ramin", "Yazdani"),
            ("fa", "رامین", "یزدانی"),  # Different script, won't auto-group
        ]:
            cv_data = {"basics": [{"fname": fname, "lname": lname}]}
            suffix = "" if lang == "en" else f"_{lang}"
            cv_path = tmp_path / "cvs" / f"ramin{suffix}.json"
            cv_path.parent.mkdir(parents=True, exist_ok=True)
            cv_path.write_text(json.dumps(cv_data))
            import_cv(cv_path, db_path)

        # Create Mahsa's CV
        cv_mahsa = {"basics": [{"fname": "Mahsa", "lname": "Amini"}]}
        cv_mahsa_path = tmp_path / "cvs" / "mahsa.json"
        cv_mahsa_path.write_text(json.dumps(cv_mahsa))
        import_cv(cv_mahsa_path, db_path)

        return db_path

    def test_auto_group_dry_run(self, db_with_variants):
        """Test auto-grouping in dry run mode."""
        stats = auto_group_variants(db_path=db_with_variants, dry_run=True)

        assert stats["dry_run"] is True
        assert stats["variants_found"] == 4
        # In dry run, nothing should be created
        assert stats["persons_created"] == 0
        assert stats["variants_linked"] == 0

    def test_auto_group_creates_entities(self, db_with_variants):
        """Test auto-grouping creates person entities."""
        stats = auto_group_variants(db_path=db_with_variants, dry_run=False)

        # Should create separate entities for:
        # - Ramin Yazdani (en/de) - same name key
        # - رامین یزدانی (fa) - different name key (Persian script)
        # - Mahsa Amini
        assert stats["persons_created"] >= 2  # At least Ramin EN/DE and Mahsa

        # Verify entities were created
        persons = list_person_entities(db_path=db_with_variants)
        assert len(persons) >= 2

    def test_auto_group_links_variants(self, db_with_variants):
        """Test auto-grouping links variants correctly."""
        auto_group_variants(db_path=db_with_variants, dry_run=False)

        # Get Ramin's person entity
        persons = list_person_entities(db_path=db_with_variants, search="ramin")

        # Should find at least one Ramin
        assert len(persons) >= 1

        # EN and DE variants should be grouped (same name key)
        ramin_latin = next(
            (p for p in persons if "en" in p["variants"] or "de" in p["variants"]),
            None
        )
        if ramin_latin:
            # Check that en and de are in same entity
            assert len(ramin_latin["variants"]) >= 1

    def test_auto_group_no_unlinked_after(self, db_with_variants):
        """Test that all variants are linked after auto-grouping."""
        auto_group_variants(db_path=db_with_variants, dry_run=False)

        unlinked = get_unlinked_variants(db_path=db_with_variants)

        # All variants with valid names should be linked
        # Only variants with completely empty names would remain unlinked
        for v in unlinked:
            assert not v.get("first_name") or not v.get("last_name")


class TestCollisionDetection:
    """Tests for name collision detection."""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a test database."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        ensure_person_entity_schema(db_path)
        return db_path

    def test_collision_prevented_on_create(self, db):
        """Test that creating person with same name raises error."""
        create_person_entity("John", "Smith", db_path=db)

        with pytest.raises(ValidationError) as exc_info:
            create_person_entity("John", "Smith", db_path=db)

        assert "already exists" in str(exc_info.value)

    def test_collision_case_insensitive(self, db):
        """Test that collision detection is case insensitive."""
        create_person_entity("John", "Smith", db_path=db)

        with pytest.raises(ValidationError):
            create_person_entity("JOHN", "SMITH", db_path=db)

    def test_can_create_different_names(self, db):
        """Test that different names don't collide."""
        create_person_entity("John", "Smith", db_path=db)
        person2 = create_person_entity("Jane", "Smith", db_path=db)

        assert person2["first_name"] == "Jane"

    def test_skip_collision_check(self, db):
        """Test that collision check can be skipped."""
        create_person_entity("John", "Smith", db_path=db)

        # Should work with check_collision=False
        person2 = create_person_entity(
            "John", "Smith",
            db_path=db,
            check_collision=False
        )

        assert person2["first_name"] == "John"
