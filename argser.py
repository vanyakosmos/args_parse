import logging
import shlex
from argparse import ArgumentParser, ArgumentTypeError, Namespace, HelpFormatter
from collections import defaultdict
from typing import Any, Iterable, List, Type, TypeVar

DEFAULT_HELP_FORMAT = "{type}, default: {default!r}. {message}"
TRUE_VALUES = {'1', 'true', 't', 'okay', 'ok', 'affirmative', 'yes', 'y', 'totally'}
FALSE_VALUES = {'0', 'false', 'f', 'no', 'n', 'nope', 'nah'}
SUB_COMMAND_MARK = '__sub_command'
SUB_COMMAND_DEST_FMT = '__{name}_sub_command__'

Args = TypeVar('Args')
logger = logging.getLogger(__name__)


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


def _green(text):
    return add_color(text, fg=32)


def _yellow(text):
    return add_color(text, fg=33)


class ColoredHelpFormatter(HelpFormatter):
    def __init__(self, prog, indent_increment=4, max_help_position=32, width=120):
        super().__init__(prog, indent_increment, max_help_position, width)

    def start_section(self, heading):
        heading = _yellow(heading)
        return super().start_section(heading)

    def add_usage(self, usage, actions, groups, prefix=None):
        if prefix is None:
            prefix = _yellow('usage') + ': '
        return super().add_usage(usage, actions, groups, prefix)

    def _format_action_invocation(self, action):
        header = super()._format_action_invocation(action)
        return _green(header)


class Arg:
    """Keywords Argument"""
    def __init__(
        self,
        dest: str = None,
        default=None,
        type=None,
        nargs=None,
        aliases: Iterable[str] = (),
        help=None,
        metavar=None,
        action='store',
        # extra
        bool_flag=True,
        one_dash=False,
        keep_default_help=True,
        help_format=DEFAULT_HELP_FORMAT,
        **kwargs,
    ):
        """
        :param dest:
        :param default:
        :param type:
        :param nargs:
        :param aliases:
        :param help:
        :param bool_flag:
            if True then read bool from argument flag: `--arg` is True, `--no-arg` is False,
            otherwise check if arg value and truthy or falsy: `--arg 1` is True `--arg no` is False
        :param one_dash: use one dash for long names: `-name` instead of `--name`
        :param keep_default_help: prepend autogenerated help message to your help message
        :param help_format: default help format
        :param kwargs: extra arguments for `parser.add_argument`
        """
        self.dest = dest
        self.type = type
        self.default = default
        self.nargs = nargs
        self.aliases = aliases
        self.help_text = help
        self._metavar = metavar
        self.action = action
        # extra
        self.bool_flag = bool_flag
        self.one_dash = one_dash
        self.keep_default_help = keep_default_help
        self.help_format = help_format
        self.extra = kwargs

    def __str__(self):
        names = ', '.join(self.names())
        type_name = getattr(self.type, '__name__', None)
        return f"Arg({names}, type={type_name}, default={self.default!r})"

    def __repr__(self):
        return str(self)

    @property
    def metavar(self):
        if self._metavar:
            return self._metavar
        if self.dest:
            return self.dest[0].upper()

    def names(self, prefix=None):
        names = [self.dest, *self.aliases]
        if prefix:
            names = [f'{prefix}{n}' for n in names]
        for name in names:
            if len(name) == 1 or self.one_dash:
                yield f"-{name}"
            else:
                yield f"--{name}"

    def params(self, exclude=(), **kwargs):
        params = dict(
            dest=self.dest,
            default=self.default,
            type=self.type,
            nargs=self.nargs,
            help=self.help,
            metavar=self.metavar,
            action=self.action,
        )
        params.update(**kwargs)
        params.update(**self.extra)
        for key in exclude:
            params.pop(key)
        return {k: v for k, v in params.items() if v is not None}

    @property
    def help(self):
        help_text = self.help_text
        if self.keep_default_help:
            typ = getattr(self.type, '__name__', '-')
            if self.nargs in ('*', '+'):
                typ = f"List[{typ}]"
            help_text = self.help_format.format(type=typ, default=self.default, message=self.help_text or '')
        return help_text

    def inject_bool(self, parser: ArgumentParser):
        if self.bool_flag and self.nargs not in ('*', '+'):
            params = self.params(exclude=('type', 'nargs', 'metavar', 'action'))
            if self.default is False:
                parser.add_argument(*self.names(), action='store_true', **params)
            elif self.default is True:
                parser.add_argument(*self.names(prefix='no-'), action='store_false', **params)
            else:
                parser.add_argument(*self.names(), action='store_true', **params)
                del params['help']
                parser.add_argument(*self.names(prefix='no-'), action='store_false', **params)
            parser.set_defaults(**{self.dest: self.default})
        else:
            params = self.params(type=str2bool)
            parser.add_argument(*self.names(), **params)

    def inject(self, parser: ArgumentParser):
        if self.type is bool:
            return self.inject_bool(parser)
        params = self.params()
        action = params.get('action')
        if action in (
            'store_const', 'store_true', 'store_false', 'append_const', 'version', 'count'
        ) and 'type' in params:
            params.pop('type')
        if action in ('store_true', 'store_false', 'count', 'version') and 'metavar' in params:
            params.pop('metavar')
        parser.add_argument(*self.names(), **params)


class PosArg(Arg):
    """Positional Argument"""
    def __init__(self, **kwargs):
        kwargs.update(bool_flag=False)
        super().__init__(**kwargs)

    @property
    def metavar(self):
        if self._metavar:
            return self._metavar

    def params(self, exclude=(), **kwargs):
        exclude += ('dest',)
        return super().params(exclude=exclude, **kwargs)

    def names(self, prefix=None):
        return [self.dest]


def stringify(args: Args):
    pairs = ', '.join(map(lambda x: f"{x[0]}={x[1]!r}", args.__dict__.items()))
    return f"{args.__class__.__name__}({pairs})"


def _get_table(args: Args):
    data = []
    for key, value in args.__dict__.items():
        if hasattr(value.__class__, SUB_COMMAND_MARK):
            sub_data = _get_table(value)
            data.extend([(f"{key}__{k}", v) for k, v in sub_data])
        else:
            data.append((key, value))
    return data


def tabulate(args: Args, **kwargs):
    from tabulate import tabulate
    kwargs.setdefault('headers', ['arg', 'value'])
    data = _get_table(args)
    return tabulate(data, **kwargs)


def print_args(args: Args, variant=None, print_fn=None, **kwargs):
    if variant == 'table':
        s = tabulate(args, **kwargs)
    elif variant:
        s = stringify(args)
    else:
        s = None
    if s:
        print_fn = print_fn or print
        print_fn(s)


def _get_nargs(typ, default):
    # just list
    if typ is list:
        if len(default or []) == 0:
            nargs = '*'
            typ = str
        else:
            nargs = '+'
            typ = type(default[0])
        return typ, nargs
    #  List or List[str] or similar
    if is_list_like_type(typ):
        if typ.__args__ and isinstance(typ.__args__[0], type):
            typ = typ.__args__[0]
        else:
            typ = str
        nargs = '*' if len(default or []) == 0 else '+'
        return typ, nargs
    # non list type
    return typ, None


def _get_fields(args_cls: Type[Args], ann: dict):
    fields_with_value = args_cls.__dict__
    fields = {k: None for k in ann if k not in fields_with_value}
    for key, value in fields_with_value.items():
        # skip built-ins and inner classes
        if key.startswith('__') or isinstance(value, type):
            continue
        fields[key] = value
    return fields


def _get_type_and_nargs(ann: dict, field_name: str, default):
    # get type from annotation or from default value or fallback to str
    typ = ann.get(field_name, str if default is None else type(default))
    logger.debug(f"init type {typ}, default: {default}")
    typ, nargs = _get_nargs(typ, default)
    # allow to auto-read only basic types
    # if typ not in (str, int, float, bool):
    #     typ = None
    logger.debug(f"type {typ}, nargs {nargs!r}")
    return typ, nargs


def _read_args(
    args_cls: Type[Args],
    override=False,
    bool_flag=True,
    one_dash=False,
    keep_default_help=True,
    help_format=DEFAULT_HELP_FORMAT,
):
    args = []
    sub_commands = {}
    ann = getattr(args_cls, '__annotations__', {})
    fields = _get_fields(args_cls, ann)
    for key, value in fields.items():  # type: str, Any
        logger.debug(f"reading {key!r}")
        if hasattr(value, SUB_COMMAND_MARK):
            sub_commands[key] = _read_args(
                value.__class__,
                bool_flag=bool_flag,
                one_dash=one_dash,
                keep_default_help=keep_default_help,
                help_format=help_format,
            )
            continue
        if isinstance(value, Arg):
            typ, nargs = _get_type_and_nargs(ann, key, value.default)
            value.dest = value.dest or key
            value.type = value.type or typ
            if value.action != 'append':
                value.nargs = value.nargs or nargs
            if override:
                value.bool_flag = bool_flag
                value.one_dash = one_dash
                value.keep_default_help = keep_default_help
                value.help_format = help_format
            logger.debug(value.__dict__)
            args.append(value)
            continue
        typ, nargs = _get_type_and_nargs(ann, key, value)
        args.append(
            Arg(
                dest=key,
                type=typ,
                default=value,
                nargs=nargs,
                # extra
                bool_flag=bool_flag,
                one_dash=one_dash,
                keep_default_help=keep_default_help,
                help_format=help_format,
            )
        )
    return args_cls, args, sub_commands


def _make_parser(name: str, args: List[Arg], sub_commands: dict, formatter_class=HelpFormatter, **kwargs):
    logger.debug(f"parser {name}:\n - {args}\n - {sub_commands}")
    parser = ArgumentParser(formatter_class=formatter_class, **kwargs)
    for arg in args:
        arg.inject(parser)

    if not sub_commands:
        return parser

    sub_parser = parser.add_subparsers(dest=SUB_COMMAND_DEST_FMT.format(name=name))

    for name, (args_cls, args, sub_p) in sub_commands.items():
        p = _make_parser(name, args, sub_p)
        parser_kwargs = getattr(args_cls, '__kwargs', {})
        parser_kwargs.setdefault('formatter_class', formatter_class)
        sub_parser.add_parser(name, parents=[p], add_help=False, **parser_kwargs)

    return parser


def _set_values(parser_name: str, res: Args, namespace: Namespace, args: List[Arg], sub_commands: dict):
    logger.debug(f'setting values for: {res}')
    for arg in args:
        setattr(res, arg.dest, namespace.__dict__.get(arg.dest))
    for name, (args_cls, args, sub_c) in sub_commands.items():
        # set values only if sub-command was chosen
        if getattr(namespace, SUB_COMMAND_DEST_FMT.format(name=parser_name)) == name:
            sub = getattr(res, name)
            setattr(res, name, sub)
            _set_values(name, sub, namespace, args, sub_c)
        # otherwise nullify sub-command
        else:
            setattr(res, name, None)
    logger.debug(f'setting complete: {res}')


def _get_all_args(args: List[Arg], sub_commands: dict) -> List[Arg]:
    res = args.copy()
    for name, (args_cls, args, sub_c) in sub_commands.items():
        res.extend(_get_all_args(args, sub_c))
    return res


def _make_shortcuts(args: List[Arg]):
    """
    Add shortcuts to arguments without defined aliases.
    """
    used = defaultdict(int)
    for arg in args:
        used[arg.dest] += 1
    for arg in args:
        if arg.aliases != ():
            continue
        # aaa -> a, aaa_bbb -> ab
        a = ''.join(map(lambda e: e[0], arg.dest.split('_')))
        if a == arg.dest:
            continue
        used[a] += 1
        if used[a] > 1:
            a = f"{a}{used[a]}"
        arg.aliases = (a,)


def sub_command(args_cls: Type[Args], **kwargs) -> Args:
    """
    :param args_cls:
    :param kwargs: additional parser kwargs
    :return:
    """
    setattr(args_cls, '__str__', stringify)
    setattr(args_cls, '__repr__', stringify)
    setattr(args_cls, '__kwargs', kwargs)
    setattr(args_cls, SUB_COMMAND_MARK, True)
    return args_cls()


def parse_args(
    args_cls: Type[Args],
    args=None,
    show=None,
    print_fn=None,
    make_shortcuts=True,
    bool_flag=True,
    one_dash=False,
    keep_default_help=True,
    help_format=DEFAULT_HELP_FORMAT,
    help_color=True,
    override=False,
    parser_kwargs=None,
    tabulate_kwargs=None,
) -> Args:
    """
    Parse arguments from string or command line and return populated instance of `args_cls`.

    :param args_cls: class with defined arguments
    :param args: arguments to parse. Either string or list of strings or None (to read from sys.args)
    :param show:
        if True - print arguments in one line
        if 'table' - print arguments as table
    :param print_fn:
    :param make_shortcuts: make short version of arguments: --abc -> -a, --abc_def -> --ad
    :param bool_flag:
        if True then read bool from argument flag: `--arg` is True, `--no-arg` is False,
        otherwise check if arg value and truthy or falsy: `--arg 1` is True `--arg no` is False
    :param one_dash: use one dash for long names: `-name` instead of `--name`
    :param keep_default_help: prepend autogenerated help message to your help message
    :param help_format: default help format
    :param help_color: add colors to the help message
    :param override: override values above on Arg's
    :param parser_kwargs: root parser kwargs
    :param tabulate_kwargs: tabulate additional kwargs
    """
    if isinstance(args, str):
        args_to_parse = shlex.split(args)
    else:
        args_to_parse = args

    args_cls, args, sub_commands = _read_args(
        args_cls,
        override=override,
        bool_flag=bool_flag,
        help_format=help_format,
        keep_default_help=keep_default_help,
        one_dash=one_dash,
    )
    if make_shortcuts:
        all_args = _get_all_args(args, sub_commands)
        _make_shortcuts(all_args)
    parser_kwargs = parser_kwargs or {}
    if help_color:
        parser_kwargs['formatter_class'] = ColoredHelpFormatter
    parser = _make_parser('root', args, sub_commands, **parser_kwargs)

    namespace = parser.parse_args(args_to_parse)
    logger.debug(namespace)

    result = sub_command(args_cls)
    _set_values('root', result, namespace, args, sub_commands)

    print_args(result, variant=show, print_fn=print_fn, **(tabulate_kwargs or {}))
    return result
