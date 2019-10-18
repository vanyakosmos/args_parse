from argparse import ArgumentTypeError, HelpFormatter, Action, SUPPRESS
from functools import partial

from argser.consts import TRUE_VALUES, FALSE_VALUES, IGNORE


def str2bool(v: str):
    """Convert string to boolean."""
    v = v.lower()
    if v in TRUE_VALUES:
        return True
    elif v in FALSE_VALUES:
        return False
    raise ArgumentTypeError('Boolean value expected.')


def is_list_like_type(t):
    """Check if provided type is List or List[str] or similar."""
    orig = getattr(t, '__origin__', None)
    return list in getattr(t, '__orig_bases__', []) or orig and issubclass(list, orig)


def add_color(text, fg, bg='', style=''):
    """
    :param text:
    :param fg: [30, 38)
    :param bg: [40, 48)
    :param style: [0, 8)
    :return:
    """
    format = ';'.join([str(style), str(fg), str(bg)])
    text = text or format
    return f'\x1b[{format}m{text}\x1b[0m'


class colors:
    red = partial(add_color, fg=31)
    green = partial(add_color, fg=32)
    yellow = partial(add_color, fg=33)
    blue = partial(add_color, fg=34)

    @classmethod
    def no(clf, text):
        return text


class ColoredHelpFormatter(HelpFormatter):
    header_color = colors.yellow
    invoc_color = colors.green
    type_color = colors.red
    default_color = colors.red

    def __init__(self, prog, indent_increment=4, max_help_position=32, width=120):
        super().__init__(prog, indent_increment, max_help_position, width)

    def start_section(self, heading):
        heading = self.header_color(heading)
        return super().start_section(heading)

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = self.header_color('usage') + ': '
        return super().add_usage(usage, actions, groups, prefix)

    def format_default_help(self, action: Action):
        if action.default == SUPPRESS:
            return
        if isinstance(action.help, str) and action.help.startswith(IGNORE):
            action.help = action.help[len(IGNORE):] or None  # cut off IGNORE
            return
        # type crutches
        if action.type is None and isinstance(action.const, bool):
            typ = bool
        elif action.default is not None:
            typ = type(action.default)
        elif action.__class__.__name__ == '_CountAction':
            typ = int
        else:
            typ = action.type
        if typ is None and action.default is None:
            return
        typ = getattr(typ, '__name__', '-')
        if action.nargs in ('*', '+') or action.__class__.__name__ == '_AppendAction':
            typ = f"List[{typ}]"
        typ = self.type_color(typ)
        default = self.default_color(repr(action.default))
        return f"{typ}, default: {default}"

    def format_action_help(self, action):
        default_help_text = self.format_default_help(action)
        if default_help_text:
            if action.help:
                return f"{default_help_text}. {action.help}"
            return default_help_text
        return action.help

    def _format_action(self, action):
        action.help = self.format_action_help(action)
        # noinspection PyProtectedMember
        text = super()._format_action(action)
        lines = text.splitlines()
        if len(lines) > 1:
            lines[0] = self.invoc_color(lines[0])
            text = '\n'.join(lines)
            return f"{text}\n"
        elif len(lines) == 1:
            line = lines[0]
            w = min(self._action_max_length, self._max_help_position)
            invoc = line[:w]
            invoc = self.invoc_color(invoc)
            help_text = line[w:]
            return f"{invoc}{help_text}\n"
        return text  # pragma: no cover
