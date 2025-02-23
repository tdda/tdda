from rich import print as rprint
from rich.console import Console
from rich.style import Style

DEBUG = False

def dprint(*args, **kw):
    if DEBUG:
        if not 'CONSOLE' in globals():
            global CONSOLE, STYLE
            CONSOLE = Console()
            STYLE = Style(color='yellow')

        CONSOLE.print(*args, **kw, style=STYLE)
