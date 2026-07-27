"""
sprezzature_cli.__main__
==================

Enables ``python -m sprezzature_cli`` — a thin entry point that delegates to the Click
group in :mod:`sprezzature_cli.cli`. No logic lives here; it exists so the package is
runnable as a module as well as via the installed ``sprezzature`` console script.

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from sprezzature_cli.cli import cli

if __name__ == "__main__":
    cli()
