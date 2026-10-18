"""ฟังก์ชันคำนวณตัวชี้วัดของบ้านสบาย ช็อป

ทุกฟังก์ชันรับ DataFrame ที่ได้จาก load_orders() เป็นพารามิเตอร์แรก
นิยามตัวชี้วัดอยู่ใน CLAUDE.md
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
DELIVERED = "จัดส่งสำเร็จ"
CANCELLED = "ยกเลิก"
RETURNED = "คืนสินค้า"


def load_orders(path: Path | str = DATA / "orders.csv") -> pd.DataFrame:
    """อ่าน orders.csv แล้วเพิ่มคอลัมน์ที่ใช้บ่อย: net, unit_cost, gp, month, date"""
    orders = pd.read_csv(path, encoding="utf-8-sig", dtype={"order_datetime": str})
    products = pd.read_csv(DATA / "products.csv", encoding="utf-8-sig")
    df = orders.merge(products[["product_id", "unit_cost"]], on="product_id", how="left")
    delivered = df["status"] == DELIVERED
    line = df["qty"] * df["unit_price"] * (1 - df["discount_pct"] / 100)
    # net/gp เป็น 0 สำหรับแถวที่ไม่ได้จัดส่งสำเร็จ จึงรวมทั้งคอลัมน์ได้ตรงตามนิยาม
    df["net"] = line.where(delivered, 0.0)
    df["gp"] = (line - df["qty"] * df["unit_cost"]).where(delivered, 0.0)
    df["month"] = df["order_datetime"].str[:7]
    df["date"] = df["order_datetime"].str[:10]
    return df


def _delivered(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == DELIVERED]


def _status_rate(df: pd.DataFrame, status: str) -> float:
    if len(df) == 0:
        return 0.0
    return (df["status"] == status).sum() / len(df) * 100


def _date_filter(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    if start_date is not None:
        df = df[df["date"] >= start_date]
    if end_date is not None:
        df = df[df["date"] <= end_date]
    return df


def net_sales(df: pd.DataFrame) -> float:
    """ยอดขายสุทธิรวม (บาท)"""
    return float(df["net"].sum())


def gross_profit(df: pd.DataFrame) -> float:
    """กำไรขั้นต้นรวม (บาท)"""
    return float(df["gp"].sum())


def aov(df: pd.DataFrame) -> float:
    """ยอดขายสุทธิเฉลี่ยต่อคำสั่งซื้อที่จัดส่งสำเร็จ (บาท)"""
    n_orders = _delivered(df)["order_id"].nunique()
    return net_sales(df) / n_orders if n_orders else 0.0


def cancel_rate(df: pd.DataFrame) -> float:
    """อัตรายกเลิกของคำสั่งซื้อทั้งหมดใน df (เปอร์เซ็นต์ 0–100)"""
    return _status_rate(df, CANCELLED)


def monthly_sales(df: pd.DataFrame) -> pd.Series:
    """ยอดขายสุทธิรายเดือน index = 'YYYY-MM' เรียงตามเวลา"""
    return df.groupby("month")["net"].sum().sort_index()


def best_month(df: pd.DataFrame) -> str:
    """เดือนที่ยอดขายสุทธิสูงสุด ('YYYY-MM')"""
    return str(monthly_sales(df).idxmax())


def channel_share(df: pd.DataFrame, channel: str, start_month: str, end_month: str) -> float:
    """สัดส่วนยอดขายสุทธิของช่องทางในช่วงเดือน start_month..end_month (รวมทั้งสองเดือน) เป็นเปอร์เซ็นต์"""
    period = df[(df["month"] >= start_month) & (df["month"] <= end_month)]
    total = period["net"].sum()
    if total == 0:
        return 0.0
    return float(period.loc[period["channel"] == channel, "net"].sum() / total * 100)


def rating_by_ship_bucket(df: pd.DataFrame) -> dict[str, float]:
    """คะแนนรีวิวเฉลี่ยตามระยะส่ง คืน dict คีย์ '1-2', '3-4', '5-6', '7+'"""
    rated = df.dropna(subset=["ship_days", "rating"])
    buckets = pd.cut(rated["ship_days"], bins=[0, 2, 4, 6, float("inf")],
                     labels=["1-2", "3-4", "5-6", "7+"])
    means = rated.groupby(buckets, observed=False)["rating"].mean()
    return {str(k): float(v) for k, v in means.items()}


def top_province(df: pd.DataFrame, region: str) -> str:
    """จังหวัดที่มียอดขายสุทธิสูงสุดในภูมิภาคที่ระบุ"""
    return str(df[df["region"] == region].groupby("province")["net"].sum().idxmax())


def avg_ship_days(df: pd.DataFrame, region: str | None = None, carrier: str | None = None,
                  start_date: str | None = None, end_date: str | None = None) -> float:
    """ระยะส่งเฉลี่ย (วัน) ตามตัวกรองที่ให้มา วันที่เป็น 'YYYY-MM-DD' และรวมทั้งสองวัน"""
    if region is not None:
        df = df[df["region"] == region]
    if carrier is not None:
        df = df[df["carrier"] == carrier]
    df = _date_filter(df, start_date, end_date)
    return float(df["ship_days"].dropna().mean())


def return_rate(df: pd.DataFrame, product_id: str | None = None,
                start_date: str | None = None, end_date: str | None = None) -> float:
    """อัตราคืนสินค้า (เปอร์เซ็นต์) ของสินค้าและช่วงวันที่ที่ระบุ"""
    if product_id is not None:
        df = df[df["product_id"] == product_id]
    df = _date_filter(df, start_date, end_date)
    return _status_rate(df, RETURNED)


def month_slice(df: pd.DataFrame, month: str) -> pd.DataFrame:
    """แถวของเดือนที่ระบุ ('YYYY-MM') ไม่แก้ df เดิม"""
    return df[df["month"] == month]


def previous_month(month: str) -> str:
    """เดือนก่อนหน้า ('YYYY-MM')"""
    return (pd.Period(month, freq="M") - 1).strftime("%Y-%m")


def top_products(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """สินค้าขายดี n อันดับตามยอดขายสุทธิ คอลัมน์ product_id, product_name, qty, net"""
    delivered = _delivered(df)
    out = (delivered.groupby(["product_id", "product_name"], as_index=False)
           .agg(qty=("qty", "sum"), net=("net", "sum")))
    return out.sort_values("net", ascending=False).head(n).reset_index(drop=True)
