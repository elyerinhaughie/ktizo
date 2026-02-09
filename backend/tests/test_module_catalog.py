"""Tests for app.services.module_catalog."""
from app.services.module_catalog import get_catalog, get_catalog_entry


REQUIRED_KEYS = {"id", "name", "scope", "category", "chart_name", "default_namespace"}


class TestGetCatalog:
    """Tests for the get_catalog function."""

    def test_returns_list(self):
        catalog = get_catalog()
        assert isinstance(catalog, list)

    def test_catalog_not_empty(self):
        assert len(get_catalog()) > 0

    def test_each_entry_has_required_keys(self):
        for entry in get_catalog():
            missing = REQUIRED_KEYS - entry.keys()
            assert not missing, f"Entry '{entry.get('id', '?')}' missing keys: {missing}"

    def test_all_ids_are_unique(self):
        ids = [entry["id"] for entry in get_catalog()]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {[x for x in ids if ids.count(x) > 1]}"

    def test_all_scopes_are_valid(self):
        valid_scopes = {"cluster", "application"}
        for entry in get_catalog():
            assert entry["scope"] in valid_scopes, (
                f"Entry '{entry['id']}' has invalid scope '{entry['scope']}'; "
                f"expected one of {valid_scopes}"
            )

    def test_all_ids_are_strings(self):
        for entry in get_catalog():
            assert isinstance(entry["id"], str)

    def test_all_names_are_strings(self):
        for entry in get_catalog():
            assert isinstance(entry["name"], str)

    def test_cluster_scope_entries_exist(self):
        scopes = {entry["scope"] for entry in get_catalog()}
        assert "cluster" in scopes

    def test_application_scope_entries_exist(self):
        scopes = {entry["scope"] for entry in get_catalog()}
        assert "application" in scopes


class TestGetCatalogEntry:
    """Tests for the get_catalog_entry lookup function."""

    def test_lookup_longhorn(self):
        entry = get_catalog_entry("longhorn")
        assert entry is not None
        assert entry["id"] == "longhorn"
        assert entry["name"] == "Longhorn"
        assert entry["scope"] == "cluster"
        assert entry["category"] == "storage"

    def test_lookup_metallb(self):
        entry = get_catalog_entry("metallb")
        assert entry is not None
        assert entry["id"] == "metallb"

    def test_privileged_namespace_modules(self):
        """Modules that require host networking or privileged containers must
        have privileged_namespace=True so the installer labels the namespace
        before helm install (prevents PodSecurity admission failures)."""
        for module_id in ("metallb", "longhorn"):
            entry = get_catalog_entry(module_id)
            assert entry is not None, f"Catalog entry '{module_id}' not found"
            assert entry.get("privileged_namespace") is True, (
                f"Catalog entry '{module_id}' must have privileged_namespace=True "
                f"or its pods will be rejected by PodSecurity admission"
            )

    def test_lookup_nonexistent_returns_none(self):
        assert get_catalog_entry("nonexistent") is None

    def test_lookup_empty_string_returns_none(self):
        assert get_catalog_entry("") is None

    def test_lookup_returns_dict(self):
        entry = get_catalog_entry("longhorn")
        assert isinstance(entry, dict)

    def test_every_catalog_entry_is_findable(self):
        """Every entry returned by get_catalog should be findable by its ID."""
        for entry in get_catalog():
            found = get_catalog_entry(entry["id"])
            assert found is not None
            assert found["id"] == entry["id"]
