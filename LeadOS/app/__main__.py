import sys
from app.web.cli import cli

if len(sys.argv) == 1:
    sys.argv.append("serve")
cli()
