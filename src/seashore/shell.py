import enum

import attrs


@enum.unique
class Output(enum.Enum):
    LOG = enum.auto()
    CAPTURE = enum.auto()
    PASS_THROUGH = enum.auto()
 
@attrs.frozen(kwargs_only=True)
class RunArgs:
    text: bool = attrs.field(default=True)
    check: bool = attrs.field(default=True)
    output: Output = attrs.field(default=PASS_THROUGH)


@attrs.frozen(kwargs_only=True)
class Shell:
    
    _subprocess_run: Callable = attrs.field(default=subprocess.run, alias="run")
    cwd: pathlib.Path = attrs.field(default=pathlib.Path(os.getcwd()))
    env: Mapping[str, str] = attrs.field(default=dict(os.environ))
    log_dir: pathlib.Path = attrs.field(default=pathlib.Path.home() / ".command-logs")

    def patch_env(self, **kwargs):
        new_env = dict(self.env)
        for key, value in kwargs.items():
            if value is None:
                new_env.pop(key, "")
            new_env[key] = value
        return attrs.evolve(self, env=new_env)
    
    def in_virtual_env(self, venv_dir):
        try:
            old_path = self.env["PATH"]
        except KeyError:
            old_path = ""
        else:
            old_path = ":" + old_path
        st_venv_dir = os.fspath(venv_dir)
        return self.patchenv(
            VIRTUALENV=venv_dir,
            PYTHON_HOME=None,
            PATH=st_venv_dir + "/bin" + old_path,
        )   

    def chdir(self, new_dir):
        return attrs.evolve(self, cwd=(self.cwd / new_dir))

    def run(self, command: Command):
        return self + command

    def run_command(self, cmd_args: Sequence[str], run_args: RunArgs) -> subprocess.CalledProcess:
        with contextlib.ExitStack() as stack:
            output_args = {}
            if run_args.output == Output.LOG:
                if run_args.text == True:
                    mode = "w+"
                else:
                    mode = "w+b"
                root_name = str(uuid.uuid4())
                stdout=stack.enter_context((self.log_dir / root_name + ".out").open(mode))
                stderr=stack.enter_context((self.log_dir / root_name + ".out").open(mode))
                output_args.update(stdout=stdout, stderr=stderr)
            elif run_args.output == Output.CAPTURE:
                output_args.update(capture_output=True)
            try:
                return self._subprocess_run(
                    cmd_args,
                    check=run_args.check,
                    text=run_args.text,
                    **output_args,
                )
            except subprocess.CalledProcessError as exc:
                return VisibleCalledProcessError.from_called_process_error(exc) from None

            
class VisibleCalledProcessError(SubprocessError):
    @classmethod
    def from_called_process_error(cls, exc: CalledProcessError):
        return cls(
            exc,
            dict(stdout=exc.stdout, stderr=exc.stderr, cmd=exc.cmd),
        )