"""E2E tests: agent-browser-agent round-trip via Playwright."""
import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e


class TestAgentBrowserRoundTrip:
    """Full round-trip: agent creates circuit → student views/modifies in browser → agent sees changes."""

    def test_create_view_modify_verify(self, e2e_server, page: Page, rc_circuit_id, circuit_manager):
        cid = rc_circuit_id

        # (b) Browser: view circuit detail
        page.goto(f"{e2e_server}/circuits/{cid}")
        expect(page.locator("body")).to_contain_text("RC Low-Pass")

        # (c) Browser: open parameter explorer
        page.goto(f"{e2e_server}/explorer/{cid}")
        r1_input = page.locator("input[name='R1__resistance']")
        expect(r1_input).to_have_value("10k")
        c1_input = page.locator("input[name='C1__capacitance']")
        expect(c1_input).to_have_value("100n")

        # (d) Student: change R1 to 22k
        r1_input.fill("22k")

        # (e) Student: click Simulate
        page.locator("button:text('Simulate')").click()
        results = page.locator("#results")
        expect(results).not_to_be_empty()

        # (f) Student: click Save changes
        page.locator("button:text('Save changes')").click()
        save_status = page.locator("#save-status")
        expect(save_status).to_contain_text("Version: 2")

        # (g) Agent: verify schema updated
        schema = circuit_manager.get_schema(cid)
        r1 = next(c for c in schema.components if c.id == "R1")
        assert r1.parameters["resistance"] == "22k"

        # (h) Agent: verify version history
        versions = circuit_manager.get_versions(cid)
        assert len(versions) == 2


class TestParameterExplorerSave:
    """Browser-level save behavior tests."""

    def test_save_no_changes_shows_message(self, e2e_server, page: Page, rc_circuit_id):
        page.goto(f"{e2e_server}/explorer/{rc_circuit_id}")
        page.locator("button:text('Save changes')").click()
        expect(page.locator("#save-status")).to_contain_text("No parameter changes")

    def test_save_multiple_parameters(self, e2e_server, page: Page, rc_circuit_id, circuit_manager):
        cid = rc_circuit_id
        page.goto(f"{e2e_server}/explorer/{cid}")

        page.locator("input[name='R1__resistance']").fill("33k")
        page.locator("input[name='C1__capacitance']").fill("220n")
        page.locator("button:text('Save changes')").click()
        expect(page.locator("#save-status")).to_contain_text("Version: 2")

        schema = circuit_manager.get_schema(cid)
        r1 = next(c for c in schema.components if c.id == "R1")
        c1 = next(c for c in schema.components if c.id == "C1")
        assert r1.parameters["resistance"] == "33k"
        assert c1.parameters["capacitance"] == "220n"

    def test_save_then_reload_shows_new_values(self, e2e_server, page: Page, rc_circuit_id):
        cid = rc_circuit_id
        page.goto(f"{e2e_server}/explorer/{cid}")

        page.locator("input[name='R1__resistance']").fill("33k")
        page.locator("button:text('Save changes')").click()
        expect(page.locator("#save-status")).to_contain_text("Version: 2")

        # Reload and verify new values persisted
        page.goto(f"{e2e_server}/explorer/{cid}")
        expect(page.locator("input[name='R1__resistance']")).to_have_value("33k")


class TestCircuitDetailView:
    """Browser tests for circuit detail page."""

    def test_circuit_detail_shows_schema(self, e2e_server, page: Page, rc_circuit_id):
        page.goto(f"{e2e_server}/circuits/{rc_circuit_id}")
        expect(page.locator("body")).to_contain_text("RC Low-Pass")

    def test_circuit_not_found_returns_404(self, e2e_server, page: Page):
        resp = page.goto(f"{e2e_server}/circuits/nonexistent-id-999")
        assert resp.status == 404
