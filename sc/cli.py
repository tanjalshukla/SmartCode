from __future__ import annotations

import typer

from .commands.admin import (
    ask,
    constraints,
    constraints_relax,
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
    preferences,
    preferences_clear,
    report,
    revoke,
    traces,
)
from .run.command import run

"""Command router with a compact public surface and legacy aliases."""

app = typer.Typer(add_completion=False)

config_app = typer.Typer(help="Configuration commands.")
rules_app = typer.Typer(help="Rule import and constraint management.")
observe_app = typer.Typer(help="Observability commands.")
dev_app = typer.Typer(help="Developer/demo utilities.")

# Compact public surface.
app.command()(init)
app.command()(doctor)
app.command()(ask)
app.command()(run)
app.command()(report)

config_app.command("set-threshold")(set_threshold)
config_app.command("set-verification-cmd")(set_verification_cmd)

rules_app.command("import")(import_rules)
rules_app.command("constraints")(constraints)
rules_app.command("constraints-relax")(constraints_relax)
rules_app.command("constraints-clear")(constraints_clear)
rules_app.command("guidelines")(guidelines)
rules_app.command("guidelines-suggest")(guidelines_suggest)
rules_app.command("guidelines-clear")(guidelines_clear)

observe_app.command("leases")(leases)
observe_app.command("traces")(traces)
observe_app.command("explain")(explain)
observe_app.command("checkin-stats")(checkin_stats)
observe_app.command("preferences")(preferences)
observe_app.command("preferences-clear")(preferences_clear)
observe_app.command("report")(report)
observe_app.command("revoke")(revoke)

dev_app.command("demo-seed")(demo_seed)

app.add_typer(config_app, name="config")
app.add_typer(rules_app, name="rules")
app.add_typer(observe_app, name="observe")
app.add_typer(dev_app, name="dev")

# Legacy command aliases kept hidden for backward compatibility.
app.command("start", hidden=True)(run)
app.command("set-threshold", hidden=True)(set_threshold)
app.command("set-verification-cmd", hidden=True)(set_verification_cmd)
app.command("import-rules", hidden=True)(import_rules)
app.command("import", hidden=True)(import_rules)
app.command("constraints", hidden=True)(constraints)
app.command("constraints-relax", hidden=True)(constraints_relax)
app.command("constraints-clear", hidden=True)(constraints_clear)
app.command("guidelines", hidden=True)(guidelines)
app.command("guidelines-suggest", hidden=True)(guidelines_suggest)
app.command("guidelines-clear", hidden=True)(guidelines_clear)
app.command("leases", hidden=True)(leases)
app.command("traces", hidden=True)(traces)
app.command("history", hidden=True)(traces)
app.command("explain", hidden=True)(explain)
app.command("checkin-stats", hidden=True)(checkin_stats)
app.command("preferences", hidden=True)(preferences)
app.command("preferences-clear", hidden=True)(preferences_clear)
app.command("demo-seed", hidden=True)(demo_seed)
app.command("revoke", hidden=True)(revoke)
