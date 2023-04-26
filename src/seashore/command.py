import .shell

@attrs.frozen()
class _NoValue:
    pass

NV = NO_VALUE = _NoValue()

@attrs.frozen()
class Eq:
    """
    Wrap a string to indicate = option

    Wrap a string to indicate that the option
    *has* to be given as ``--name=value``
    rather than the usually equivalent and
    more automation-friendly ``--name value``

    :code:`git show --format`, I'm looking
    at you.
    """

    content: str

@functools.singledispatch
def _keyword_arguments(value, key):
    raise ValueError("cannot process", value)

@_keyword_arguments.register(_NoValue)
def _keyword_arguments_eq(value, key):
    yield key
    
@_keyword_arguments.register(Eq)
def _keyword_arguments_eq(value, key):
    yield key + '=' + value.content

@_keyword_arguments.register(str)
def _keyword_arguments_str(value, key):
    yield key
    yield value

@_keyword_arguments.register(int)
def _keyword_arguments_int(value, key):
    yield key
    yield str(value)

@_keyword_arguments.register(list)
def _keyword_arguments_list(value, key):
    for thing in value:
        yield key
        yield thing

@_keyword_arguments.register(dict)
def _keyword_arguments_dict(value, key):
    for in_k, thing in value.items():
        yield key
        yield '{}={}'.format(in_k, thing)

@attrs.frozen
class _Arguments:
    _args: Sequence[str]
    _kwargs: Mapping[str, str]

    def __iter__(self):
        for key, value in self._kwargs.items():
            key = "--" + key.replace("_", "-")
            yield from _keyword_arguments(value, key)
        yield from self._args
        
def args(*args: str, **kwargs: str) -> _Iterable[str]:
    return _Arguments(args, kwargs)
    
@attrs.define()
class CommandsBuilder:
    commands_defined: Any = attrs.field(factory=dict)
    
    def add_command(self, name: str, value: Optional[Command]=None):
        if value is None:
            value = Command(name)
        self.commands_defined[name] = value
    
    def build(self):
        return CommandsCollection(self.commands_defined)

    
    
@attrs.frozen
class Command:
    _subcommand: Sequence[str]
    _cmd_args: Sequence[str]
    _run_args: RunArgs = attrs.field(factory=RunArgs)
    
    def __getattr__(self, name):
        name = name.replace("_", "-")
        return attrs.evolve(
            self,
            subcommand=list(self._subcommand) + [name],
        )
    
    def __call__(self, cmd_args: Optional[Iterable[str]]=None, **kwargs):
        if cmd_args is not None:
            new_cmd_args = list(self._cmd_args)
            new_cmd_args.extend(cmd_args)
        else:
            new_cmd_args = self._cmd_args
        return attrs.evolve(
            self,
            cmd_args=new_cmd_args,
            run_args=attrs.evolve(
                self._run_args,
                **kwargs,
            ),
        )
    
    def __radd__(self, /, a_shell: Shell):
        total_args = list(self._subcommand)
        total_args.extend(self._cmd_args)
        return shell.run(a_shell, total_args, run_args)
