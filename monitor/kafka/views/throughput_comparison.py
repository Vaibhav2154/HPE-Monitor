import shutil
from monitor.config import console
from monitor.kafka.collectors import prom_range, KAFKA_TOPIC, KAFKA_GROUP
from monitor.utils import press_enter_to_return

_BLOCKS = " ▁▂▃▄▅▆▇█"

def display_throughput_comparison(timeframe: str = "1h", minutes: int = 30):
    """
    Draw K7 (produced) and K8 (consumed) as stacked sparklines
    on the same time axis so the gap between them is visible.
    """
    console.rule(
        f"[bold yellow]📊 K7 vs K8 — Produced vs Consumed Rate  "
        f"[dim](last {minutes} min)[/dim][/bold yellow]"
    )

    promql_k7 = (f'sum(rate(kafka_topic_partition_current_offset'
                 f'{{topic="{KAFKA_TOPIC}"}}[60s]))')
    promql_k8 = (f'sum(rate(kafka_consumergroup_current_offset'
                 f'{{topic="{KAFKA_TOPIC}",consumergroup="{KAFKA_GROUP}"}}[60s]))')

    s7 = prom_range(promql_k7, minutes=minutes)
    s8 = prom_range(promql_k8, minutes=minutes)

    if not s7 and not s8:
        console.print("[yellow]No Prometheus data available.[/yellow]")
        return

    term_w = shutil.get_terminal_size((100, 30)).columns
    width  = max(40, term_w - 20)

    def _sparkline(series, color):
        values = [v for _, v in series]
        if len(values) > width:
            step   = len(values) / width
            values = [values[int(i * step)] for i in range(width)]
        if not values:
            return "", 0, 0, 0
        mn, mx = min(values), max(values)
        spark  = ""
        for v in values:
            idx   = int((v - mn) / (mx - mn + 1e-9) * 8) if mx != mn else 4
            idx   = max(0, min(8, idx))
            spark += f"[{color}]{_BLOCKS[idx]}[/{color}]"
        avg = sum(values) / len(values)
        return spark, values[-1], mn, mx, avg

    if s7:
        sp7, lat7, mn7, mx7, av7 = _sparkline(s7, "yellow")
        console.print(f"  [yellow]{'K7 Produced Rate':<22}[/yellow]  "
                      f"latest=[yellow]{lat7:.3f}[/yellow]  "
                      f"[dim]avg={av7:.3f}  max={mx7:.3f}[/dim]")
        console.print(f"  {'':22}  {sp7}")
        console.print()

    if s8:
        sp8, lat8, mn8, mx8, av8 = _sparkline(s8, "cyan")
        console.print(f"  [cyan]{'K8 Consumed Rate':<22}[/cyan]  "
                      f"latest=[cyan]{lat8:.3f}[/cyan]  "
                      f"[dim]avg={av8:.3f}  max={mx8:.3f}[/dim]")
        console.print(f"  {'':22}  {sp8}")
        console.print()

    if s7 and s8:
        lat7 = [v for _, v in s7][-1] if s7 else 0
        lat8 = [v for _, v in s8][-1] if s8 else 0
        gap  = lat7 - lat8
        gc   = "red" if gap > 0.5 else ("yellow" if gap > 0 else "green")
        console.print(
            f"  [bold]Current gap (prod − cons):[/bold]  "
            f"[{gc}]{gap:+.3f} msgs/sec[/{gc}]  "
            f"[dim]({'producer ahead' if gap > 0 else 'consumer caught up'})[/dim]\n"
        )
    press_enter_to_return()