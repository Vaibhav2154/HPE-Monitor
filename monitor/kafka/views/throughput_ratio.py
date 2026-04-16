import shutil
import datetime
from monitor.config import console
from monitor.kafka.collectors import prom_range, KAFKA_TOPIC, KAFKA_GROUP, METRIC_META
from monitor.kafka.display_utils import score_color, fmt_score
from monitor.utils import press_enter_to_return
from rich.panel import Panel

def display_throughput_ratio(timeframe: str = "1h", minutes: int = 30):
    """Display K2 — Message Throughput Ratio (prod/cons) as a terminal bar chart."""
    key    = "K2"
    _, name, unit = METRIC_META[key]
    promql = (
        f'sum(rate(kafka_topic_partition_current_offset{{topic="{KAFKA_TOPIC}"}}[60s])) / '
        f'clamp_min(sum(rate(kafka_consumergroup_current_offset'
        f'{{topic="{KAFKA_TOPIC}",consumergroup="{KAFKA_GROUP}"}}[60s])),0.001)'
    )

    series = prom_range(promql, minutes=minutes)
    if not series:
        console.print(
            Panel(
                f"[yellow]No Prometheus data for [bold]{name}[/bold].\n\n"
                "[dim]Possible reasons:\n"
                "  • Prometheus is not reachable\n"
                "  • kafka_exporter is not scraping\n"
                "  • No messages produced in this window[/dim]",
                border_style="yellow", expand=False
            )
        )
        press_enter_to_return()
        return

    term_w  = shutil.get_terminal_size((100, 30)).columns
    width   = max(40, term_w - 12)
    values  = [v for _, v in series]
    times   = [t for t, _ in series]

    if len(values) > width:
        step   = len(values) / width
        values = [values[int(i * step)] for i in range(width)]
        times  = [times[int(i * step)]  for i in range(width)]

    mn, mx  = min(values), max(values)
    avg_v   = sum(values) / len(values)
    latest  = values[-1]

    def to_score(v):
        return min(max(v - 1.0, 0.0), 1.0) * 100

    console.rule(
        f"[bold yellow]📉 {key} — {name}  "
        f"[dim](last {minutes} min | {len(series)} points)[/dim][/bold yellow]"
    )

    rows      = 8
    bar_lines = ["" for _ in range(rows)]

    for v in values:
        score = to_score(v)
        c     = score_color(score, key)
        level = int((v - mn) / (mx - mn + 1e-9) * rows) if mx != mn else 1
        level = max(1, min(level, rows))
        for row in range(rows):
            if (rows - 1 - row) < level:
                bar_lines[row] += f"[{c}]█[/{c}]"
            else:
                bar_lines[row] += " "

    y_ticks = {0: f"{mx:.2f}", 2: f"{(mx*0.75):.2f}",
               4: f"{(mx*0.5):.2f}", 6: f"{(mx*0.25):.2f}", 7: f"{mn:.2f}"}
    console.print()
    for i, line in enumerate(bar_lines):
        lbl    = y_ticks.get(i, "")
        prefix = f"[dim]{lbl:>8}[/dim] │"
        console.print(prefix + line)
    console.print("         └" + "─" * min(len(values), width))

    if times:
        t_s = datetime.datetime.fromtimestamp(times[0]).strftime("%H:%M")
        t_e = datetime.datetime.fromtimestamp(times[-1]).strftime("%H:%M")
        pad = max(0, min(len(values), width) - 10)
        console.print(f"    [dim]     {t_s}{' ' * pad}{t_e}  IST[/dim]")

    mid   = len(values) // 2
    first = sum(values[:mid])  / max(mid, 1)
    last  = sum(values[mid:])  / max(len(values[mid:]), 1)
    trend = ("↑ Rising"  if last > first + (mx * 0.02) else
             "↓ Falling" if last < first - (mx * 0.02) else
             "→ Stable")
    tc    = "red" if trend.startswith("↑") else "green" if trend.startswith("↓") else "cyan"
    sc    = to_score(latest)
    lc    = score_color(sc, key)

    console.print(
        f"\n  [bold]Stats:[/bold]  "
        f"Latest=[bold {lc}]{latest:.3f}[/bold {lc}]  [dim]{unit}[/dim]   "
        f"Min=[green]{mn:.3f}[/green]   "
        f"Max=[red]{mx:.3f}[/red]   "
        f"Avg=[cyan]{avg_v:.3f}[/cyan]   "
        f"Trend=[{tc}]{trend}[/{tc}]\n"
    )
    press_enter_to_return()