class BuildscadError(Exception):
    """Base exception for all buildscad errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class BuildscadConfigError(BuildscadError):
    """Base exception for configuration-related errors."""

    pass


class BuildscadMissingConfigFile(BuildscadConfigError):
    """Raised when a required configuration file is not found."""

    pass


class BuildscadInvalidProperty(BuildscadConfigError):
    """Raised when a property has an invalid format or value."""

    pass


class BuildscadMissingProperty(BuildscadConfigError):
    """Raised when a required property is missing from the configuration."""

    pass


class BuildscadAssemblyParseError(BuildscadError):
    """Raised when an assembly string cannot be parsed."""

    pass


class BuildscadDependencyError(BuildscadError):
    """Base exception for dependency-related errors."""

    pass


class BuildscadInvalidGitHubUrl(BuildscadDependencyError):
    """Raised when a GitHub URL is malformed or unsupported."""

    pass


class BuildscadCloneFailed(BuildscadDependencyError):
    """Raised when a git clone operation fails."""

    def __init__(self, url: str, ref: str, stderr: str = "") -> None:
        self.url = url
        self.ref = ref
        self.stderr = stderr
        message = f"Failed to clone {url} (ref: {ref})"
        if stderr:
            message += f": {stderr.strip()}"
        self.message = message
        super().__init__(message)


class BuildscadCircularDependency(BuildscadDependencyError):
    """Raised when a circular dependency is detected."""

    pass


class BuildscadBuildError(BuildscadError):
    """Base exception for build-related errors."""

    pass


class BuildscadOpenSCADNotFound(BuildscadBuildError):
    """Raised when the OpenSCAD executable cannot be found."""

    pass


class BuildscadOpenSCADFailed(BuildscadBuildError):
    """Raised when an OpenSCAD invocation fails."""

    def __init__(self, cmd: list[str], returncode: int, stderr: str = "") -> None:
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        message = f"OpenSCAD command failed (exit code {returncode}): {' '.join(cmd)}"
        if stderr:
            message += f"\n{stderr.strip()}"
        self.message = message
        super().__init__(message)


class BuildscadAssemblyFileNotFound(BuildscadBuildError):
    """Raised when an assembly .scad file does not exist on disk."""

    pass


class BuildscadOpenSCADVersionMismatch(BuildscadBuildError):
    """Raised when installed OpenSCAD version doesn't meet dependency requirements."""

    def __init__(self, dep_name: str, required: str, installed: str) -> None:
        self.dep_name = dep_name
        self.required = required
        self.installed = installed
        self.message = (
            f"OpenSCAD version mismatch for dependency '{dep_name}': "
            f"requires {required}, found {installed}"
        )
        super().__init__(self.message)


class BuildscadFileError(BuildscadError):
    """Base exception for file system operation errors."""

    pass


class BuildscadPermissionDenied(BuildscadFileError):
    """Raised when a file system operation is denied due to permissions."""

    pass


class BuildscadDiskFull(BuildscadFileError):
    """Raised when a write operation fails due to insufficient disk space."""

    pass


class BuildscadInvalidOutputType(BuildscadError):
    """Raised when an output type string is not valid."""

    def __init__(self, value: str, valid: str) -> None:
        self.value = value
        self.valid = valid
        self.message = f"'{value}' is not a valid output type. Valid types: {valid}"
        super().__init__(self.message)


class BuildscadInvalidColorScheme(BuildscadError):
    """Raised when a color scheme string is not valid."""

    def __init__(self, value: str, valid: str) -> None:
        self.value = value
        self.valid = valid
        self.message = f"Invalid color scheme value '{value}'. Valid schemes: {valid}"
        super().__init__(self.message)
