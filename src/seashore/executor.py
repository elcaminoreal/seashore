"""
Executor
--------

Construct command-line lists.

:const:`NO_VALUE` -- indicate an option with no value (a boolean option)
"""
from __future__ import annotations
import functools
from typing import Any

import attrs

NO_VALUE = object()

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
def _keyword_arguments(_value, key):
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

def cmd(binary, *args, **kwargs):
    """
    Construct a command line for a "modern UNIX" command.

    Modern UNIX command do a closely-related-set-of-things and do it well.
    Examples include :code:`apt-get` or :code:`git`.

    :param binary: the name of the command
    :param args: positional arguments (put last)
    :param kwargs: options
    :returns: list of arguments that is suitable to be passed to :code:`subprocess.Popen`
              and friends.

    When specifying options, the following assumptions are made:

    * Option names begin with :code:`--` and any :code:`_` is assumed to be a :code:`-`
    * If the value is :code:`NO_VALUE`, this is a "naked" option.
    * If the value is a string or an int, these are presented as the value of the option.
    * If the value is a list, the option will be repeated multiple times.
    * If the value is a dict, the option will be repeated multiple times, and
      its values will be :code:`<KEY>=<VALUE>`.
    """
    ret = [binary]
    ret.extend(args)
    for key, value in kwargs.items():
        key = '--' + key.replace('_', '-')
        ret.extend(_keyword_arguments(value, key))
    return ret

@attr.frozen()
class _PreparedCommand:
    _args: Sequence[str]
    _shell: Any
    
    def __call__(
    def batch(self, *args, **kwargs):
        """Run the shell's batch"""
        return self._shell.batch(self._cmd, *args, **kwargs)

    def interactive(self, *args, **kwargs):
        """Run the shell's interactive"""
        return self._shell.interactive(self._cmd, *args, **kwargs)

    def redirect(self, *args, **kwargs):
        """Run the shell's redirect"""
        return self._shell.redirect(self._cmd, *args, **kwargs)

    def popen(self, *args, **kwargs):
        """Run the shell's popen"""
        return self._shell.popen(self._cmd, *args, **kwargs)


@attr.frozen()
class Command:

    """
    A command is something that can be bound to an executor.
    Commands get automatically bound if defined as members of an executor.

    :param name: the name of a 'Modern UNIX' command (i.e., something with subcommands).
    """
    _name: str

    def bind(self, executor, _dummy=None):
        """
        Bind a command to an executor.

        :param executor: the executor to bind to
        :returns: something that has methods :code:`batch`, :code:`interactive` and :code:`popen`
                  methods.
        """
        return _ExecutoredCommand(executor, self._name)

    __get__ = bind

@attr.frozen()
class _ExecutoredCommand:

    _executor: str
    _name: str

    def __call__(self, *args, **kwargs):
        return self._executor.prepare(self._name, *args, **kwargs)

    def __getattr__(self, subcommand):
        subcommand = subcommand.rstrip('_').replace('_', '-')
        return functools.partial(self._executor.prepare, self._name, subcommand)

@attr.frozen()
class Executor:

    """
    Executes commands.

    Init parameters:

    :param shell: something that actually runs subprocesses.
                  Should match the interface of :code:`Shell`.
    :param pypi: optional. An extra index URL.
    :param commands: optional. An iterable of strings which are commands to suppport.

    The default commands that are supported are :code:`git`, :code:`pip`, :code:`conda`,
    :code:`docker`, :code:`docker_machine`.
    """

    _shell: Any
    _pypi: Optional[str] = attrs.field(default=None)
    _commands: attrs.field(factory=set, converter=set)

    git = Command('git')
    pip = Command('pip')
    conda = Command('conda')
    docker = Command('docker')

    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError(name) # Reserved Python names not supported as commands
        if name not in self._commands:
            raise AttributeError(name)
        name = name.replace('_', '-')
        return Command(name).bind(self)

    def add_command(self, name):
        """
        Add a new command.

        :param name: name of command
        """
        self._commands.add(name)

    def command(self, args):
        """
        Prepare a command from a raw argument list.

        :param args: argument list
        :returns: something that supports batch/interactive/popen
        """
        return _PreparedCommand(args, shell=self._shell.clone())

    def patch_env(self, **kwargs):
        """
        Return a new executor where the environment is patched with the given attributes

        :param kwargs: new environment variables
        :returns: new executor with a shell with a patched environment.
        """
        new_shell = self._shell.clone()
        for key, value in kwargs.items():
            new_shell.setenv(key, value)
        return attr.evolve(self, shell=new_shell)

    def chdir(self, path):
        """
        Return a new executor where the working directory is different.

        :param path: new path
        :returns: new executor with a different working directory
        """
        new_shell = self._shell.clone()
        new_shell.chdir(path)
        return attr.evolve(self, shell=new_shell)

    def in_virtualenv(self, envpath):
        """
        Return an executor where all Python commands would point at a specific virtual environment.

        :param envpath: path to virtual environment
        :returns: a new executor
        """
        env = dict(VIRTUAL_ENV=envpath, PYTHONHOME=None)
        binpath = envpath + "/bin"
        try:
            base_path = ":" + new_shell.getenv('PATH')
        except KeyError:
            base_path = ""
        env.update(PATH=base_path + bin_path)
        return self.patch_env(**env)

    def pip_install(self, pkg_ids, index_url=None):
        """
        Use pip to install packages

        :param pkg_ids: an list of package names
        :param index_url: (optional) an extra PyPI-compatible index
        :raises: :code:`ProcessError` if the installation fails
        """
        kwargs = {}
        if index_url is None:
            index_url = self._pypi
        if index_url is not None:
            kwargs.update(extra_index_url=index_url)
        mycmd = self.pip.install(*pkg_ids, **kwargs)
        return mycmd.batch()

    def conda_install(self, pkg_ids, channels=None):
        """
        Use conda to install packages

        :param pkg_ids: an list of package names
        :param channels: (optional) a list of channels to install from
        :raises: :code:`ProcessError` if the installation fails
        """
        mycmd = self.conda.install(
            quiet=NO_VALUE,
            yes=NO_VALUE,
            show_channel_urls=NO_VALUE,
            channel=(channels or []),
            *pkg_ids,
        )
        return mycmd.batch()
