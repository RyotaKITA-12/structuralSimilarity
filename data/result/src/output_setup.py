def function1(var1, var2, var3, var4):
            var1.extend(var2(var3.path.join(var4, var5, "*.h")))
    return var1, var2, var3, var4, var5

# Autodetecting setup.py script for building the Python extensions

import argparse
import importlib._bootstrap
import importlib.machinery
import importlib.util
import logging
import os
import re
import shlex
import sys
import sysconfig
import warnings
from glob import glob, escape
import _osx_support


try:
    import subprocess
    del subprocess
    SUBPROCESS_BOOTSTRAP = False
except ImportError:
    # Bootstrap Python: distutils.spawn uses subprocess to build C extensions,
    # subprocess requires C extensions built by setup.py like _posixsubprocess.
    #
    # Use _bootsubprocess which only uses the os module.
    #
    # It is dropped from sys.modules as soon as all C extension modules
    # are built.
    import _bootsubprocess
    sys.modules['subprocess'] = _bootsubprocess
    del _bootsubprocess
    SUBPROCESS_BOOTSTRAP = True


with warnings.catch_warnings():
    # bpo-41282 (PEP 632) deprecated distutils but setup.py still uses it
    warnings.filterwarnings(
        "ignore",
        "The distutils package is deprecated",
        DeprecationWarning
    )
    warnings.filterwarnings(
        "ignore",
        "The distutils.sysconfig module is deprecated, use sysconfig instead",
        DeprecationWarning
    )

    from distutils.command.build_ext import build_ext
    from distutils.command.build_scripts import build_scripts
    from distutils.command.install import install
    from distutils.command.install_lib import install_lib
    from distutils.core import Extension, setup
    from distutils.errors import CCompilerError, DistutilsError
    from distutils.spawn import find_executable


# This global variable is used to hold the list of modules to be disabled.
DISABLED_MODULE_LIST = []

# --list-module-names option used by Tools/scripts/generate_module_names.py
LIST_MODULE_NAMES = False


logging.basicConfig(format='%(message)s', level=logging.INFO)
log = logging.getLogger('setup')


def get_platform():
    # Cross compiling
    if "_PYTHON_HOST_PLATFORM" in os.environ:
        return os.environ["_PYTHON_HOST_PLATFORM"]

    # Get value of sys.platform
    if sys.platform.startswith('osf1'):
        return 'osf1'
    return sys.platform


CROSS_COMPILING = ("_PYTHON_HOST_PLATFORM" in os.environ)
HOST_PLATFORM = get_platform()
MS_WINDOWS = (HOST_PLATFORM == 'win32')
CYGWIN = (HOST_PLATFORM == 'cygwin')
MACOS = (HOST_PLATFORM == 'darwin')
AIX = (HOST_PLATFORM.startswith('aix'))
VXWORKS = ('vxworks' in HOST_PLATFORM)
CC = os.environ.get("CC")
if not CC:
    CC = sysconfig.get_config_var("CC")


SUMMARY = """
Python is an interpreted, interactive, object-oriented programming
language. It is often compared to Tcl, Perl, Scheme or Java.

Python combines remarkable power with very clear syntax. It has
modules, classes, exceptions, very high level dynamic data types, and
dynamic typing. There are interfaces to many system calls and
libraries, as well as to various windowing systems (X11, Motif, Tk,
Mac, MFC). New built-in modules are easily written in C or C++. Python
is also usable as an extension language for applications that need a
programmable interface.

The Python implementation is portable: it runs on many brands of UNIX,
on Windows, DOS, Mac, Amiga... If your favorite system isn't
listed here, it may still be supported, if there's a C compiler for
it. Ask around on comp.lang.python -- or just try compiling Python
yourself.
"""

CLASSIFIERS = """
Development Status :: 6 - Mature
License :: OSI Approved :: Python Software Foundation License
Natural Language :: English
Programming Language :: C
Programming Language :: Python
Topic :: Software Development
"""


def run_command(cmd):
    status = os.system(cmd)
    return os.waitstatus_to_exitcode(status)


# Set common compiler and linker flags derived from the Makefile,
# reserved for building the interpreter and the stdlib modules.
# See bpo-21121 and bpo-35257
def set_compiler_flags(compiler_flags, compiler_py_flags_nodist):
    flags = sysconfig.get_config_var(compiler_flags)
    py_flags_nodist = sysconfig.get_config_var(compiler_py_flags_nodist)
    sysconfig.get_config_vars()[compiler_flags] = flags + ' ' + py_flags_nodist


def add_dir_to_list(dirlist, dir):
    """Add the directory 'dir' to the list 'dirlist' (after any relative
    directories) if:

    1) 'dir' is not already in 'dirlist'
    2) 'dir' actually exists, and is a directory.
    """
    if dir is None or not os.path.isdir(dir) or dir in dirlist:
        return
    for i, path in enumerate(dirlist):
        if not os.path.isabs(path):
            dirlist.insert(i + 1, dir)
            return
    dirlist.insert(0, dir)


def sysroot_paths(make_vars, subdirs):
    """Get the paths of sysroot sub-directories.

    * make_vars: a sequence of names of variables of the Makefile where
      sysroot may be set.
    * subdirs: a sequence of names of subdirectories used as the location for
      headers or libraries.
    """

    dirs = []
    for var_name in make_vars:
        var = sysconfig.get_config_var(var_name)
        if var is not None:
            m = re.search(r'--sysroot=([^"]\S*|"[^"]+")', var)
            if m is not None:
                sysroot = m.group(1).strip('"')
                for subdir in subdirs:
                    if os.path.isabs(subdir):
                        subdir = subdir[1:]
                    path = os.path.join(sysroot, subdir)
                    if os.path.isdir(path):
                        dirs.append(path)
                break
    return dirs


MACOS_SDK_ROOT = None
MACOS_SDK_SPECIFIED = None

def macosx_sdk_root():
    """Return the directory of the current macOS SDK.

    If no SDK was explicitly configured, call the compiler to find which
    include files paths are being searched by default.  Use '/' if the
    compiler is searching /usr/include (meaning system header files are
    installed) or use the root of an SDK if that is being searched.
    (The SDK may be supplied via Xcode or via the Command Line Tools).
    The SDK paths used by Apple-supplied tool chains depend on the
    setting of various variables; see the xcrun man page for more info.
    Also sets MACOS_SDK_SPECIFIED for use by macosx_sdk_specified().
    """
    global MACOS_SDK_ROOT, MACOS_SDK_SPECIFIED

    # If already called, return cached result.
    if MACOS_SDK_ROOT:
        return MACOS_SDK_ROOT

    cflags = sysconfig.get_config_var('CFLAGS')
    m = re.search(r'-isysroot\s*(\S+)', cflags)
    if m is not None:
        MACOS_SDK_ROOT = m.group(1)
        MACOS_SDK_SPECIFIED = MACOS_SDK_ROOT != '/'
    else:
        MACOS_SDK_ROOT = _osx_support._default_sysroot(
            sysconfig.get_config_var('CC'))
        MACOS_SDK_SPECIFIED = False

    return MACOS_SDK_ROOT


def macosx_sdk_specified():
    """Returns true if an SDK was explicitly configured.

    True if an SDK was selected at configure time, either by specifying
    --enable-universalsdk=(something other than no or /) or by adding a
    -isysroot option to CFLAGS.  In some cases, like when making
    decisions about macOS Tk framework paths, we need to be able to
    know whether the user explicitly asked to build with an SDK versus
    the implicit use of an SDK when header files are no longer
    installed on a running system by the Command Line Tools.
    """
    global MACOS_SDK_SPECIFIED

    # If already called, return cached result.
    if MACOS_SDK_SPECIFIED:
        return MACOS_SDK_SPECIFIED

    # Find the sdk root and set MACOS_SDK_SPECIFIED
    macosx_sdk_root()
    return MACOS_SDK_SPECIFIED


def is_macosx_sdk_path(path):
    """
    Returns True if 'path' can be located in a macOS SDK
    """
    return ( (path.startswith('/usr/') and not path.startswith('/usr/local'))
                or path.startswith('/System/Library')
                or path.startswith('/System/iOSSupport') )


def grep_headers_for(function, headers):
    for header in headers:
        with open(header, 'r', errors='surrogateescape') as f:
            if function in f.read():
                return True
    return False


def find_file(filename, std_dirs, paths):
    """Searches for the directory where a given file is located,
    and returns a possibly-empty list of additional directories, or None
    if the file couldn't be found at all.

    'filename' is the name of a file, such as readline.h or libcrypto.a.
    'std_dirs' is the list of standard system directories; if the
        file is found in one of them, no additional directives are needed.
    'paths' is a list of additional locations to check; if the file is
        found in one of them, the resulting list will contain the directory.
    """
    if MACOS:
        # Honor the MacOSX SDK setting when one was specified.
        # An SDK is a directory with the same structure as a real
        # system, but with only header files and libraries.
        sysroot = macosx_sdk_root()

    # Check the standard locations
    for dir_ in std_dirs:
        f = os.path.join(dir_, filename)

        if MACOS and is_macosx_sdk_path(dir_):
            f = os.path.join(sysroot, dir_[1:], filename)

        if os.path.exists(f): return []

    # Check the additional directories
    for dir_ in paths:
        f = os.path.join(dir_, filename)

        if MACOS and is_macosx_sdk_path(dir_):
            f = os.path.join(sysroot, dir_[1:], filename)

        if os.path.exists(f):
            return [dir_]

    # Not found anywhere
    return None


def find_library_file(compiler, libname, std_dirs, paths):
    result = compiler.find_library_file(std_dirs + paths, libname)
    if result is None:
        return None

    if MACOS:
        sysroot = macosx_sdk_root()

    # Check whether the found file is in one of the standard directories
    dirname = os.path.dirname(result)
    for p in std_dirs:
        # Ensure path doesn't end with path separator
        p = p.rstrip(os.sep)

        if MACOS and is_macosx_sdk_path(p):
            # Note that, as of Xcode 7, Apple SDKs may contain textual stub
            # libraries with .tbd extensions rather than the normal .dylib
            # shared libraries installed in /.  The Apple compiler tool
            # chain handles this transparently but it can cause problems
            # for programs that are being built with an SDK and searching
            # for specific libraries.  Distutils find_library_file() now
            # knows to also search for and return .tbd files.  But callers
            # of find_library_file need to keep in mind that the base filename
            # of the returned SDK library file might have a different extension
            # from that of the library file installed on the running system,
            # for example:
            #   /Applications/Xcode.app/Contents/Developer/Platforms/
            #       MacOSX.platform/Developer/SDKs/MacOSX10.11.sdk/
            #       usr/lib/libedit.tbd
            # vs
            #   /usr/lib/libedit.dylib
            if os.path.join(sysroot, p[1:]) == dirname:
                return [ ]

        if p == dirname:
            return [ ]

    # Otherwise, it must have been in one of the additional directories,
    # so we have to figure out which one.
    for p in paths:
        # Ensure path doesn't end with path separator
        p = p.rstrip(os.sep)

        if MACOS and is_macosx_sdk_path(p):
            if os.path.join(sysroot, p[1:]) == dirname:
                return [ p ]

        if p == dirname:
            return [p]
    else:
        assert False, "Internal error: Path not found in std_dirs or paths"


def validate_tzpath():
    base_tzpath = sysconfig.get_config_var('TZPATH')
    if not base_tzpath:
        return

    tzpaths = base_tzpath.split(os.pathsep)
    bad_paths = [tzpath for tzpath in tzpaths if not os.path.isabs(tzpath)]
    if bad_paths:
        raise ValueError('TZPATH must contain only absolute paths, '
                         + f'found:\n{tzpaths!r}\nwith invalid paths:\n'
                         + f'{bad_paths!r}')


def find_module_file(module, dirlist):
    """Find a module in a set of possible folders. If it is not found
    return the unadorned filename"""
    dirs = find_file(module, [], dirlist)
    if not dirs:
        return module
    if len(dirs) > 1:
        log.info(f"WARNING: multiple copies of {module} found")
    return os.path.abspath(os.path.join(dirs[0], module))


class PyBuildExt(build_ext):

    def __init__(self, dist):
        build_ext.__init__(self, dist)
        self.srcdir = None
        self.lib_dirs = None
        self.inc_dirs = None
        self.config_h_vars = None
        self.failed = []
        self.failed_on_import = []
        self.missing = []
        self.disabled_configure = []
        if '-j' in os.environ.get('MAKEFLAGS', ''):
            self.parallel = True

    def add(self, ext):
        self.extensions.append(ext)

    def addext(self, ext, *, update_flags=True):
        """Add extension with Makefile MODULE_{name} support
        """
        if update_flags:
            self.update_extension_flags(ext)

        state = sysconfig.get_config_var(f"MODULE_{ext.name.upper()}")
        if state == "yes":
            self.extensions.append(ext)
        elif state == "disabled":
            self.disabled_configure.append(ext.name)
        elif state == "missing":
            self.missing.append(ext.name)
        elif state == "n/a":
            # not available on current platform
            pass
        else:
            # not migrated to MODULE_{name} yet.
            self.announce(
                f'WARNING: Makefile is missing module variable for "{ext.name}"',
                level=2
            )
            self.extensions.append(ext)

    def update_extension_flags(self, ext):
        """Update extension flags with module CFLAGS and LDFLAGS

        Reads MODULE_{name}_CFLAGS and _LDFLAGS

        Distutils appends extra args to the compiler arguments. Some flags like
        -I must appear earlier, otherwise the pre-processor picks up files
        from system inclue directories.
        """
        upper_name = ext.name.upper()
        # Parse compiler flags (-I, -D, -U, extra args)
        cflags = sysconfig.get_config_var(f"MODULE_{upper_name}_CFLAGS")
        if cflags:
            for token in shlex.split(cflags):
                switch = token[0:2]
                value = token[2:]
                if switch == '-I':
                    ext.include_dirs.append(value)
                elif switch == '-D':
                    key, _, val = value.partition("=")
                    if not val:
                        val = None
                    ext.define_macros.append((key, val))
                elif switch == '-U':
                    ext.undef_macros.append(value)
                else:
                    ext.extra_compile_args.append(token)

        # Parse linker flags (-L, -l, extra objects, extra args)
        ldflags = sysconfig.get_config_var(f"MODULE_{upper_name}_LDFLAGS")
        if ldflags:
            for token in shlex.split(ldflags):
                switch = token[0:2]
                value = token[2:]
                if switch == '-L':
                    ext.library_dirs.append(value)
                elif switch == '-l':
                    ext.libraries.append(value)
                elif (
                    token[0] != '-' and
                    token.endswith(('.a', '.o', '.so', '.sl', '.dylib'))
                ):
                    ext.extra_objects.append(token)
                else:
                    ext.extra_link_args.append(token)

        return ext

    def set_srcdir(self):
        self.srcdir = sysconfig.get_config_var('srcdir')
        if not self.srcdir:
            # Maybe running on Windows but not using CYGWIN?
            raise ValueError("No source directory; cannot proceed.")
        self.srcdir = os.path.abspath(self.srcdir)

    def remove_disabled(self):
        # Remove modules that are present on the disabled list
        extensions = [ext for ext in self.extensions
                      if ext.name not in DISABLED_MODULE_LIST]
        # move ctypes to the end, it depends on other modules
        ext_map = dict((ext.name, i) for i, ext in enumerate(extensions))
        if "_ctypes" in ext_map:
            ctypes = extensions.pop(ext_map["_ctypes"])
            extensions.append(ctypes)
        self.extensions = extensions

    def update_sources_depends(self):
        # Fix up the autodetected modules, prefixing all the source files
        # with Modules/.
        # Add dependencies from MODULE_{name}_DEPS variable
        moddirlist = [
            # files in Modules/ directory
            os.path.join(self.srcdir, 'Modules'),
            # files relative to build base, e.g. libmpdec.a, libexpat.a
            os.getcwd()
        ]

        # Fix up the paths for scripts, too
        self.distribution.scripts = [os.path.join(self.srcdir, filename)
                                     for filename in self.distribution.scripts]

        # Python header files
        include_dir = escape(sysconfig.get_path('include'))
        headers = [sysconfig.get_config_h_filename()]
        headers.extend(glob(os.path.join(include_dir, "*.h")))
headers, glob, os, include_dir, 'cpython' = function1(headers, glob, os, include_dir)
headers, glob, os, include_dir, 'internal' = function1(headers, glob, os, include_dir)

        for ext in self.extensions:
            ext.sources = [ find_module_file(filename, moddirlist)
                            for filename in ext.sources ]
            # Update dependencies from Makefile
            makedeps = sysconfig.get_config_var(f"MODULE_{ext.name.upper()}_DEPS")
            if makedeps:
                # remove backslashes from line break continuations
                ext.depends.extend(
                    dep for dep in makedeps.split() if dep != "\\"
                )
            ext.depends = [
                find_module_file(filename, moddirlist) for filename in ext.depends
            ]
            # re-compile extensions if a header file has been changed
            ext.depends.extend(headers)
