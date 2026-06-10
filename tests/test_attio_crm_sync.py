from pathlib import Path

import pytest

import attio_orders_sync


TEST_SYNC_LOG = Path(__file__).with_name("_attio_order_sync_log.json")


@pytest.fixture(autouse=True)
def clean_sync_log(monkeypatch):
    if TEST_SYNC_LOG.exists():
        TEST_SYNC_LOG.unlink()
    monkeypatch.setattr(attio_orders_sync, "ORDER_SYNC_LOG_PATH", TEST_SYNC_LOG)
    yield
    if TEST_SYNC_LOG.exists():
        TEST_SYNC_LOG.unlink()


class FakeAttioClient:
    def __init__(self, api_key: str = "test_attio_key"):
        self.api_key = api_key
        self.posts = []
        self.fail = False

    async def _post(self, path, body):
        if self.fail:
            raise RuntimeError("attio_5xx")
        self.posts.append((path, body))
        name = path.strip("/").split("/")[1] if "/objects/" in path else "note"
        return {"data": {"id": {"record_id": f"{name}_{len(self.posts)}"}}}

    async def close(self):
        return None


def _paid_order(**overrides):
    order = {
        "order_id": "ds_attio_001",
        "mollie_id": "tr_attio_001",
        "product": "predd",
        "company_name": "Scan Target B.V.",
        "kvk_number": "12345678",
        "domain": "target.example",
        "customer_email": "buyer@acme.example",
        "delivery_email": "delivery@acme.example",
        "amount": "399.00",
        "currency": "EUR",
        "status": "paid",
        "scan_status": "delivered",
        "delivery_status": "ready",
        "created_at": "2026-06-09T12:00:00Z",
    }
    order.update(overrides)
    return order


def _posts_for(client, path):
    return [body for posted_path, body in client.posts if posted_path == path]


@pytest.mark.asyncio
async def test_order_sync_maps_buyer_to_person_company_and_target_to_note(monkeypatch):
    client = FakeAttioClient()
    syncer = attio_orders_sync.AttioOrderSync(
        client=client,
        sync_log_path=TEST_SYNC_LOG,
        live_enabled=True,
    )

    result = await syncer.push_order(_paid_order())

    assert result["status"] == "synced"
    people = _posts_for(client, "/objects/people/records")
    companies = _posts_for(client, "/objects/companies/records")
    deals = _posts_for(client, "/objects/deals/records")
    notes = _posts_for(client, "/notes")

    assert people
    assert people[0]["matching_attribute"] == "email_addresses"
    person_values = people[0]["data"]["values"]
    assert {"email_address": "buyer@acme.example"} in person_values["email_addresses"]
    assert {"email_address": "delivery@acme.example"} in person_values["email_addresses"]

    assert companies
    company_values = companies[0]["data"]["values"]
    assert companies[0]["matching_attribute"] == "domains"
    assert company_values["domains"] == [{"domain": "acme.example"}]
    assert "Scan Target" not in str(company_values)
    assert "12345678" not in str(company_values)
    assert "Dealfront" not in str(company_values)

    assert deals
    assert "Scan Target B.V." in deals[0]["data"]["values"]["description"][0]["value"]
    assert "12345678" in deals[0]["data"]["values"]["description"][0]["value"]

    assert notes
    note = notes[0]["data"]
    assert note["parent_object"] == "companies"
    assert "Scan-target / onderwerp van scan" in note["content"]
    assert "Scan Target B.V." in note["content"]
    assert "12345678" in note["content"]


@pytest.mark.asyncio
async def test_order_sync_is_idempotent_by_order_id(monkeypatch):
    client = FakeAttioClient()
    syncer = attio_orders_sync.AttioOrderSync(
        client=client,
        sync_log_path=TEST_SYNC_LOG,
        live_enabled=True,
    )

    first = await syncer.push_order(_paid_order())
    second = await syncer.push_order(_paid_order())

    assert first["status"] == "synced"
    assert second == {"status": "already_synced", "order_id": "ds_attio_001"}
    assert len(client.posts) == 4


@pytest.mark.asyncio
async def test_free_email_domain_creates_person_but_no_company(monkeypatch):
    client = FakeAttioClient()
    syncer = attio_orders_sync.AttioOrderSync(
        client=client,
        sync_log_path=TEST_SYNC_LOG,
        live_enabled=True,
    )

    result = await syncer.push_order(
        _paid_order(customer_email="buyer@gmail.com", delivery_email="")
    )

    assert result["status"] == "synced"
    assert _posts_for(client, "/objects/people/records")
    assert _posts_for(client, "/objects/companies/records") == []
    note = _posts_for(client, "/notes")[0]["data"]
    assert note["parent_object"] == "people"


@pytest.mark.asyncio
async def test_attio_errors_are_best_effort_and_not_marked_synced(monkeypatch):
    client = FakeAttioClient()
    client.fail = True
    syncer = attio_orders_sync.AttioOrderSync(
        client=client,
        sync_log_path=TEST_SYNC_LOG,
        live_enabled=True,
    )

    result = await syncer.push_order(_paid_order())

    assert result["status"] == "failed"
    assert result["order_id"] == "ds_attio_001"
    assert "attio_5xx" in result["error"]
    assert TEST_SYNC_LOG.exists() is False


@pytest.mark.asyncio
async def test_missing_attio_api_key_is_noop(monkeypatch):
    client = FakeAttioClient(api_key="")
    syncer = attio_orders_sync.AttioOrderSync(
        client=client,
        sync_log_path=TEST_SYNC_LOG,
        live_enabled=True,
    )

    result = await syncer.push_order(_paid_order())

    assert result == {"status": "no_api_key", "order_id": "ds_attio_001"}
    assert client.posts == []


@pytest.mark.asyncio
async def test_live_push_requires_explicit_dpa_gate(monkeypatch):
    monkeypatch.delenv("DUESIGHT_ATTIO_ORDER_SYNC_ENABLED", raising=False)
    monkeypatch.delenv("DUESIGHT_ATTIO_DPA_CONFIRMED", raising=False)
    client = FakeAttioClient()
    syncer = attio_orders_sync.AttioOrderSync(
        client=client,
        sync_log_path=TEST_SYNC_LOG,
    )

    result = await syncer.push_order(_paid_order())

    assert result == {"status": "disabled", "order_id": "ds_attio_001"}
    assert client.posts == []


def test_status_counts_open_orders(monkeypatch):
    syncer = attio_orders_sync.AttioOrderSync(
        client=FakeAttioClient(),
        sync_log_path=TEST_SYNC_LOG,
        live_enabled=False,
    )
    syncer.synced_order_ids = {"ds_attio_001"}

    status = syncer.status(
        [
            _paid_order(order_id="ds_attio_001"),
            _paid_order(order_id="ds_attio_002"),
        ]
    )

    assert status["status"] == "disabled"
    assert status["orders"] == 2
    assert status["synced"] == 1
    assert status["open"] == 1
    assert status["open_order_ids"] == ["ds_attio_002"]
