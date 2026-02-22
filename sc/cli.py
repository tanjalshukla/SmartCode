from __future__ import annotations

import typer

from .commands.admin import (
    ask,
    constraints,
    constraints_clear,
    doctor,
    guidelines,
    guidelines_clear,
    guidelines_suggest,
    import_rules,
    init,
    set_threshold,
    set_verification_cmd,
)
from .commands.observe import (
    checkin_stats,
    demo_seed,
    explain,
    leases,
    report,
    revoke,
    traces,
)
from .run.command import run

"""Command router"""

app = typer.Typer(add_completion=False)

app.command()(doctor)
app.command()(ask)
app.command()(init)
app.command()(set_threshold)
app.command("set-verification-cmd")(set_verification_cmd)
app.command("import-rules")(import_rules)
app.command("import")(import_rules)
app.command()(constraints)
app.command()(guidelines)
app.command("guidelines-suggest")(guidelines_suggest)
app.command("guidelines-clear")(guidelines_clear)
app.command("constraints-clear")(constraints_clear)
app.command()(run)
app.command("start")(run)
app.command()(leases)
app.command()(traces)
app.command("history")(traces)
app.command()(explain)
app.command("checkin-stats")(checkin_stats)
app.command()(report)
app.command("demo-seed")(demo_seed)
app.command()(revoke)
