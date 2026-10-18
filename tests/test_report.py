"""test ของรายงานรายเดือน (W4-B)"""
import pytest

from src import metrics as m
from src import report


@pytest.fixture(scope="module")
def df():
    return m.load_orders()


def test_report_march_2026(df):
    r = report.build_report(df, "2026-03")
    assert r["net_sales"] == pytest.approx(1_147_155, abs=1)
    assert r["prev_month"] == "2026-02"
    assert r["prev_net_sales"] == pytest.approx(962_379, abs=1)
    assert r["change_pct"] == pytest.approx(19.2, abs=0.05)
    assert len(r["top5"]) == 5
    assert sum(r["status_counts"].values()) == r["rows"]


def test_report_markdown(df):
    text = report.render_markdown(report.build_report(df, "2026-03"))
    assert "฿1,147,155" in text
    assert "5 สินค้าขายดี" in text


def test_report_sample_not_hardcoded():
    sample = m.load_orders(m.DATA / "orders_sample_80.csv")
    month = m.monthly_sales(sample).index[0]
    assert report.build_report(sample, month)["net_sales"] == pytest.approx(m.net_sales(m.month_slice(sample, month)))
