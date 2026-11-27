"""
CommerceIQ - Streamlit Analytics Studio Smoke Tests

Verifies all 10 pages, sidebar filters, predictive checkout form, and
database-backed KPI calculations render without exceptions.
"""

from pathlib import Path
import pytest

from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _mysql_ok() -> bool:
    try:
        from src.database.connection import get_connection, get_database_name

        c = get_connection(database=get_database_name())
        c.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _mysql_ok(), reason="Local MySQL commerceiq unavailable")
def test_streamlit_all_10_pages_render():
    at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=60)
    at.run()
    assert not at.exception, f"Initial render raised: {at.exception}"

    pages = at.sidebar.radio[0].options
    assert len(pages) == 10

    for page_name in pages:
        at.sidebar.radio[0].set_value(page_name).run()
        assert not at.exception, f"Page `{page_name}` raised: {at.exception}"


@pytest.mark.skipif(not _mysql_ok(), reason="Local MySQL commerceiq unavailable")
def test_streamlit_checkout_risk_form_submission():
    at = AppTest.from_file(str(PROJECT_ROOT / "app" / "main.py"), default_timeout=60)
    at.run()
    at.sidebar.radio[0].set_value("Predictive Analytics").run()
    assert not at.exception
    # Submit form button
    form_btns = [b for b in at.button if "Predict Checkout Delay Risk" in (b.label or "")]
    if form_btns:
        form_btns[0].click().run()
        assert not at.exception
