"""สร้างรายงานยอดขายรายเดือน reports/monthly_report.md

รัน: python -m src.report 2026-03
ทุกตัวเลขมาจากฟังก์ชันใน src/metrics.py
"""
import re
import sys
from pathlib import Path

import pandas as pd

from src import metrics as m

REPORTS = Path(__file__).resolve().parent.parent / "reports"


def build_report(df: pd.DataFrame, month: str) -> dict:
    """คำนวณตัวเลขของรายงานเดือน month ('YYYY-MM')"""
    cur = m.month_slice(df, month)
    if cur.empty:
        raise ValueError(f"ไม่มีข้อมูลเดือน {month}")
    prev_month = m.previous_month(month)
    prev = m.month_slice(df, prev_month)
    net = m.net_sales(cur)
    prev_net = m.net_sales(prev) if not prev.empty else None
    change = (net - prev_net) / prev_net * 100 if prev_net else None
    return {
        "month": month,
        "rows": len(cur),
        "status_counts": cur["status"].value_counts().to_dict(),
        "net_sales": net,
        "prev_month": prev_month,
        "prev_net_sales": prev_net,
        "change_pct": change,
        "top5": m.top_products(cur, 5),
        "cancel_rate": m.cancel_rate(cur),
        "return_rate": m.return_rate(cur),
    }


def render_markdown(r: dict) -> str:
    lines = [
        f"# รายงานยอดขายประจำเดือน {r['month']} · บ้านสบาย ช็อป",
        "",
        "## ตรวจข้อมูล",
        "",
        f"- จำนวนคำสั่งซื้อในเดือน: {r['rows']:,} แถว",
    ]
    lines += [f"- {k}: {v:,}" for k, v in r["status_counts"].items()]
    lines += ["", "## ตัวเลขหลัก", "", "| ตัวชี้วัด | ค่า |", "|---|---|",
              f"| ยอดขายสุทธิ | ฿{r['net_sales']:,.0f} |"]
    if r["prev_net_sales"] is None:
        lines.append(f"| เทียบเดือนก่อน ({r['prev_month']}) | ไม่มีข้อมูล |")
    else:
        lines.append(f"| ยอดขายสุทธิเดือนก่อน ({r['prev_month']}) | ฿{r['prev_net_sales']:,.0f} |")
        lines.append(f"| เปลี่ยนแปลง | {r['change_pct']:+.1f}% |")
    lines += [f"| อัตรายกเลิก | {r['cancel_rate']:.2f}% |",
              f"| อัตราคืนสินค้า | {r['return_rate']:.2f}% |",
              "", "## 5 สินค้าขายดี (ตามยอดขายสุทธิ)", "",
              "| อันดับ | สินค้า | จำนวนชิ้น | ยอดขายสุทธิ |", "|---|---|---|---|"]
    for i, p in enumerate(r["top5"].itertuples(), 1):
        lines.append(f"| {i} | {p.product_name} ({p.product_id}) | {p.qty:,} | ฿{p.net:,.0f} |")
    lines += ["", "นิยาม: ยอดขายสุทธิ = qty × unit_price × (1 − discount_pct/100) "
              "เฉพาะ status = \"จัดส่งสำเร็จ\" ไม่รวมค่าส่ง", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not re.fullmatch(r"\d{4}-\d{2}", argv[0]):
        print("ใช้: python -m src.report YYYY-MM", file=sys.stderr)
        return 2
    report = build_report(m.load_orders(), argv[0])
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / "monthly_report.md"
    out.write_text(render_markdown(report), encoding="utf-8")
    print(f"บันทึก {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
