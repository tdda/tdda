from rich import print as rprint
from rich.console import Console
from rich.table import Table


rprint("[italic red]Hello[/italic red] World!", locals())

console = Console()

print(console.color_system)


from io import StringIO
from rich.console import Console
console = Console(file=StringIO())
console.print("[bold red]Hello[/] World")
str_output = console.file.getvalue()

rprint(str_output)
rprint('foo')


table = Table(title="Star Wars Movies")

table.add_column("Released", justify="right", style="blue", no_wrap=True)
table.add_column("Title", style="red")
table.add_column("Box Office", justify="right", style="green")

table.add_row("[bold dim red]Dec 20, 2019[/bold dim red]", "Star Wars: The Rise of Skywalker", "$952,110,690")
table.add_row("May 25, 2018", "Solo: A Star Wars Story", "$393,151,347")
table.add_row("Dec 15, 2017", "Star Wars Ep. V111: The Last Jedi", "$1,332,539,889")
table.add_row("Dec 16, 2016", "Rogue One: A Star Wars Story", "$1,332,439,889")

console = Console()
console.print(table)

import pandas as pd

df = pd.DataFrame({
    'i': range(10),
    'sq': [i * i for i in range(10)],
    'cube': [i * i * i for i in range(10)],
    'mask' : [2, 0] * 5
})
print(df)
df2 = df[['i', 'cube']][df['mask'] > 0]
print(df2)
print()
print(df2.shape)
for row in range(df2.shape[0]):
    for col in range(df2.shape[1]):
        print(row, col, df2.iat[row,col], type(df2.iat[row,col]),
              df2.iat[row,col].item(), type(df2.iat[row,col].item()))

print(df.index)
print()
print(df2.index)
