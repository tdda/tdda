class ReferenceTestParams:
    def __init__(self):
        self.left_colour = 'red'
        self.right_colour = 'green'
        self.mono = False
        self.bw = False
        self.left_prefix = '< '
        self.right_prefix = '> '
        self.vertical = None
        self.force_val_prefixes = False

    def left_diff(self, value, force_prefix=None):
        annotated = self.left_annotated(value, force_prefix)
        if self.bw or self.mono:
            return f'[bold]{annotated}[/bold]'
        else:
            colour = self.left_colour
            return f'[{colour}]{annotated}[/{colour}]'

    def right_diff(self, value, force_prefix=None):
        annotated = self.right_annotated(value, force_prefix)
        if self.bw or self.mono:
            return f'[bold]{annotated}[/bold]'
        else:
            colour = self.right_colour
            return f'[{colour}]{annotated}[/{colour}]'

    def left_annotated(self, value, force_prefix=None):
        prefix = self.left_prefix if force_prefix else ''
        return f'{prefix}{value}'

    def right_annotated(self, value, force_prefix=None):
        prefix = self.right_prefix if force_prefix else ''
        return f'{prefix}{value}'

    def common(self, value, dim_if_not_bw=False):
        if self.mono or (dim_if_not_bw and not self.bw):
            return f'[dim]{value}[/dim]'
        else:
            return str(value)

    def set_colours(self, left, right):
        self.left_colour, self.right_colour = left.lower(), right.lower()
        # possibly validate

    def set_prefixes(self, left, right):
        self.left_prefix, self.right_prefix = left, right
        # possibly validate

    def stripped_prefixes(self, pre='\n'):
        return (pre + self.left_prefix.strip().replace(':', ''),
                pre + self.right_prefix.strip().replace(':', ''))
