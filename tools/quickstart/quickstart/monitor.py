import os
from textwrap import fill

import click

from quickstart.constants import MONITOR_DIR, MONITOR_REPORTS_DIR, MONITOR_STATE_PATH
from quickstart.utils import is_monitor_prepared


def setup_interactively():
    click.echo("\n")

    if is_monitor_prepared():
        click.echo("The monitor has already been set up.")
        return

    click.echo(
        fill(
            "The monitor is a tool that observes the Trustlines blockchain and creates reports "
            "of offline and equivocating validators."
        )
    )

    os.makedirs(MONITOR_DIR, exist_ok=True)
    os.makedirs(MONITOR_REPORTS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MONITOR_STATE_PATH), exist_ok=True)

    click.echo("Monitor setup complete.")
