from dataclasses import dataclass
from datetime import date, datetime
import os
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

from core.domain import StageType

BAR_INTERVAL_MIN = 15


def _set_korean_font():
    preferred = [
        "NanumGothic",
        "NanumSquareRound",
        "NanumSquare",
        "NanumBarunGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "Malgun Gothic",
        "AppleGothic",
    ]
    env_font = os.environ.get("KOREAN_FONT")
    if env_font:
        preferred.insert(0, env_font)
    env_path = os.environ.get("KOREAN_FONT_PATH")
    if env_path and os.path.exists(env_path):
        font_manager.fontManager.addfont(env_path)
        name = font_manager.FontProperties(fname=env_path).get_name()
        mpl.rcParams["font.family"] = name
        mpl.rcParams["axes.unicode_minus"] = False
        return
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in preferred:
        if name in available:
            mpl.rcParams["font.family"] = name
            mpl.rcParams["axes.unicode_minus"] = False
            return


_set_korean_font()


@dataclass(frozen=True)
class TradeMark:
    symbol: str
    side: str
    ts: datetime
    price: float
    qty: int
    name: str = ""


def resample_15m_close(df: pd.DataFrame) -> pd.Series:
    df = df.sort_values("dt")
    series = pd.to_numeric(df["price_close"], errors="coerce")
    series = pd.Series(series.values, index=df["dt"])
    series = series.resample("15min", label="right", closed="right").last()
    return series.dropna()


def resample_15m_volume(df: pd.DataFrame, target_index: pd.Index) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=float)
    df = df.sort_values("dt").copy()
    df["volume_cum"] = pd.to_numeric(df["volume_cum"], errors="coerce").fillna(0)
    df["trade_date"] = df["dt"].dt.date
    df["volume_delta"] = df.groupby("trade_date")["volume_cum"].diff()
    df["volume_delta"] = df["volume_delta"].fillna(df["volume_cum"])
    df["volume_delta"] = df["volume_delta"].clip(lower=0)
    series = pd.Series(df["volume_delta"].values, index=df["dt"])
    series = series.resample("15min", label="right", closed="right").sum()
    return series.reindex(target_index).fillna(0)


def calc_stage_series(prices: pd.Series) -> List[int]:
    ewm_5 = prices.ewm(span=5).mean()
    ewm_20 = prices.ewm(span=20).mean()
    ewm_40 = prices.ewm(span=40).mean()
    diff = ewm_5 - ewm_40
    signal = diff.ewm(span=9).mean()

    stages: List[int] = []
    for idx in range(len(prices)):
        s5 = ewm_5.iat[idx]
        s20 = ewm_20.iat[idx]
        s40 = ewm_40.iat[idx]
        crossed_golden = diff.iat[idx] > signal.iat[idx]
        crossed_dead = diff.iat[idx] <= signal.iat[idx]

        if s5 > s20 and s20 > s40:
            stage = StageType.SELL_1 if crossed_dead else StageType.BUY_3
        elif s5 > s40 and s20 <= s40:
            stage = StageType.BUY_2
        elif s5 <= s40 and s5 > s20:
            stage = StageType.BUY_1
        elif s5 < s20 and s20 < s40:
            stage = StageType.BUY_1 if crossed_golden else StageType.SELL_3
        elif s5 < s40 and s20 >= s40:
            stage = StageType.SELL_2
        else:
            stage = StageType.SELL_1
        stages.append(stage)
    return stages


STAGE_COLORS = {
    StageType.SELL_3: "#f8c9c9",
    StageType.SELL_2: "#fbd9d9",
    StageType.SELL_1: "#fdeaea",
    StageType.BUY_1: "#e3f2ff",
    StageType.BUY_2: "#cfe7ff",
    StageType.BUY_3: "#b9dcff",
}

STAGE_LABELS = {
    StageType.SELL_3: "SELL_3",
    StageType.SELL_2: "SELL_2",
    StageType.SELL_1: "SELL_1",
    StageType.BUY_1: "BUY_1",
    StageType.BUY_2: "BUY_2",
    StageType.BUY_3: "BUY_3",
}


def plot_weekly_chart(
    symbol: str,
    prices: pd.Series,
    volumes: pd.Series,
    stages: List[int],
    trades: List[TradeMark],
    broker: str,
    output_path: Path,
    title_suffix: str,
):
    if prices.empty:
        return
    fig, (ax, ax_vol) = plt.subplots(
        2,
        1,
        figsize=(14, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    x_values, day_boundaries, day_anchor_map, hour_ticks = _build_compressed_axis(
        prices.index, broker
    )
    ax.plot(x_values, prices.values, color="#111111", linewidth=1.2, zorder=3)

    for idx, _ in enumerate(prices.index):
        end_x = x_values[idx]
        start_x = end_x - BAR_INTERVAL_MIN
        color = STAGE_COLORS.get(stages[idx], "#ffffff")
        ax.axvspan(start_x, end_x, color=color, alpha=0.45, zorder=0)

    _annotate_stage_blocks(ax, x_values, stages)

    for boundary, day in day_boundaries:
        ax.axvline(boundary, color="#444444", linewidth=1.0, alpha=0.5, zorder=1)
        ax_vol.axvline(boundary, color="#444444", linewidth=1.0, alpha=0.5, zorder=1)
    if day_boundaries:
        ax_vol.set_xticks([b for b, _ in day_boundaries])
        ax_vol.set_xticklabels([day.strftime("%m-%d") for _, day in day_boundaries])
    if hour_ticks:
        ax_vol.set_xticks([x for x, _ in hour_ticks], minor=True)
        ax_vol.set_xticklabels([label for _, label in hour_ticks], minor=True)
        ax_vol.tick_params(axis="x", which="minor", labelsize=8, rotation=0, pad=6)

    for idx, trade in enumerate(trades):
        color = "#1f77b4" if trade.side == "buy" else "#d62728"
        marker = "^" if trade.side == "buy" else "v"
        trade_x = _map_trade_to_axis(
            trade.ts, prices.index, broker, day_boundaries, day_anchor_map
        )
        if trade_x is None:
            continue
        trade_y = _nearest_price(prices, trade.ts)
        if trade_y is None:
            continue
        ax.scatter(
            [trade_x],
            [trade_y],
            s=70,
            marker=marker,
            color=color,
            edgecolor="#111111",
            linewidth=0.4,
            zorder=5,
        )
        y_min, y_max = ax.get_ylim()
        offset_dir = 1 if (idx % 2 == 0) else -1
        offset_scale = 0.035 + (idx % 3) * 0.02
        y_text = trade_y + (y_max - y_min) * offset_scale * offset_dir
        x_text = trade_x + ((idx % 3) - 1) * BAR_INTERVAL_MIN * 0.6
        side_label = "BUY" if trade.side == "buy" else "SELL"
        label = f"{side_label}\n{trade.price:.2f}\n{trade.qty}"
        ax.text(
            x_text,
            y_text,
            label,
            fontsize=8,
            color=color,
            rotation=0,
            va="center",
            ha="center",
            zorder=6,
            bbox=dict(
                boxstyle="round,pad=0.2",
                facecolor="white",
                alpha=0.6,
                edgecolor="none",
            ),
        )

    ax.set_title(f"{symbol} {title_suffix}".strip())
    ax.set_ylabel("Price")
    ax.tick_params(axis="x", labelbottom=False)
    ax_vol.set_ylabel("Vol")
    ax_vol.set_xlabel("Date")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

    if not volumes.empty:
        ax_vol.bar(
            x_values,
            volumes.values,
            width=BAR_INTERVAL_MIN * 0.8,
            color="#9aa0a6",
            alpha=0.6,
            zorder=2,
        )
        ax_vol.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def _nearest_price(prices: pd.Series, ts: datetime) -> Optional[float]:
    if prices.empty:
        return None
    idx = prices.index
    try:
        pos = idx.get_indexer([ts], method="nearest")[0]
    except Exception:
        return None
    if pos < 0 or pos >= len(prices):
        return None
    return float(prices.iloc[pos])


def _annotate_stage_blocks(ax, x_values: List[float], stages: List[int]) -> None:
    if not x_values or not stages:
        return
    y_min, y_max = ax.get_ylim()
    y_text = y_max - (y_max - y_min) * 0.06
    last_label_x: Optional[float] = None
    start = 0
    for i in range(1, len(stages) + 1):
        if i == len(stages) or stages[i] != stages[start]:
            stage = stages[start]
            label = STAGE_LABELS.get(stage)
            if label:
                mid = (x_values[start] + x_values[i - 1]) / 2.0
                if (
                    last_label_x is not None
                    and abs(mid - last_label_x) < BAR_INTERVAL_MIN * 4
                ):
                    start = i
                    continue
                ax.text(
                    mid,
                    y_text,
                    label,
                    fontsize=7,
                    color="#333333",
                    va="top",
                    ha="center",
                    zorder=2,
                )
                last_label_x = mid
            start = i


def _session_start_minute(broker: str) -> int:
    if broker == "hantoo":
        return 9 * 60 + 30
    return 9 * 60


def _day_start_ts(day: date, broker: str) -> datetime:
    base_minutes = _session_start_minute(broker)
    hour = base_minutes // 60
    minute = base_minutes % 60
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _build_compressed_axis(
    timestamps: Sequence[datetime], broker: str
) -> Tuple[
    List[float],
    List[Tuple[float, date]],
    Dict[date, datetime],
    List[Tuple[float, str]],
]:
    day_points: Dict[date, List[datetime]] = {}
    for ts in timestamps:
        day_points.setdefault(ts.date(), []).append(ts)
    days = sorted(day_points.keys())
    offsets: Dict[date, float] = {}
    current_offset = 0.0
    boundaries: List[Tuple[float, date]] = []
    anchors: Dict[date, datetime] = {}
    hour_ticks: List[Tuple[float, str]] = []
    for day in days:
        session_start = _day_start_ts(day, broker)
        first_point = min(day_points[day])
        day_start = first_point if first_point >= session_start else session_start
        latest = max(day_points[day])
        day_length = max(0.0, (latest - day_start).total_seconds() / 60.0)
        offsets[day] = current_offset
        anchors[day] = day_start
        boundaries.append((current_offset, day))
        tick_cursor = 0.0
        while tick_cursor <= day_length:
            absolute_minutes = _session_start_minute(broker) + int(tick_cursor)
            hour_label = (absolute_minutes // 60) % 24
            hour_ticks.append((current_offset + tick_cursor, f"{hour_label:02d}"))
            tick_cursor += 60.0
        current_offset += day_length + BAR_INTERVAL_MIN

    x_values: List[float] = []
    for ts in timestamps:
        day_start = anchors[ts.date()]
        minutes_since = (ts - day_start).total_seconds() / 60.0
        if minutes_since < 0:
            minutes_since = 0.0
        x_values.append(offsets[ts.date()] + minutes_since)
    return x_values, boundaries, anchors, hour_ticks


def _map_trade_to_axis(
    trade_ts: datetime,
    price_times: Sequence[datetime],
    broker: str,
    day_boundaries: List[Tuple[float, date]],
    day_anchor_map: Dict[date, datetime],
) -> Optional[float]:
    if len(price_times) == 0:
        return None
    day = trade_ts.date()
    day_points = [ts for ts in price_times if ts.date() == day]
    if not day_points:
        return None
    day_start = day_anchor_map.get(day)
    if day_start is None:
        day_start = _day_start_ts(day, broker)
    latest = max(day_points)
    min_minutes = max(0.0, (trade_ts - day_start).total_seconds() / 60.0)
    max_minutes = max(0.0, (latest - day_start).total_seconds() / 60.0)
    clamped = min(min_minutes, max_minutes)
    offset_lookup = {day_key: offset for offset, day_key in day_boundaries}
    base_offset = offset_lookup.get(day)
    if base_offset is None:
        return None
    return base_offset + clamped

