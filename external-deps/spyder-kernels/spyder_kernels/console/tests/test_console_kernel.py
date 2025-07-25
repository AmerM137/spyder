# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © 2018- Spyder Kernels Contributors
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Tests for the console kernel.
"""

# Standard library imports
import ast
import asyncio
from collections import namedtuple
from contextlib import contextmanager
import inspect
import os
import os.path as osp
import random
from subprocess import Popen, PIPE
import sys
from textwrap import dedent
import time
import uuid

# Test imports
from flaky import flaky
from IPython.core import release as ipython_release
from jupyter_core import paths
from jupyter_client import BlockingKernelClient
import numpy as np
import pytest

# Local imports
from spyder_kernels.comms.commbase import CommBase
from spyder_kernels.customize.spyderpdb import SpyderPdb
from spyder_kernels.utils.iofuncs import iofunctions
from spyder_kernels.utils.pythonenv import PythonEnvType
from spyder_kernels.utils.test_utils import get_kernel, get_log_text

# =============================================================================
# Constants and utility functions
# =============================================================================
FILES_PATH = os.path.dirname(os.path.realpath(__file__))
TIMEOUT = 15
SETUP_TIMEOUT = 60

# We declare this constant immediately before the test, as determining
# that TURTLE_ACTIVE is True will briefly pop up a window, similar to the
# windows that will pop up during the test itself.
TURTLE_ACTIVE = False
try:
    import turtle
    turtle.Screen()
    turtle.bye()
    TURTLE_ACTIVE = True
except:
    pass


@contextmanager
def setup_kernel(cmd):
    """start an embedded kernel in a subprocess, and wait for it to be ready

    This function was taken from the ipykernel project.
    We plan to remove it.

    Yields
    -------
    client: jupyter_client.BlockingKernelClient connected to the kernel
    """
    kernel = Popen([sys.executable, '-c', cmd], stdout=PIPE, stderr=PIPE)
    try:
        connection_file = os.path.join(
            paths.jupyter_runtime_dir(),
            'kernel-%i.json' % kernel.pid,
        )
        # wait for connection file to exist, timeout after 5s
        tic = time.time()
        while (
            not os.path.exists(connection_file)
            and kernel.poll() is None
            and time.time() < tic + SETUP_TIMEOUT
        ):
            time.sleep(0.1)

        if kernel.poll() is not None:
            o, e = kernel.communicate()
            raise IOError("Kernel failed to start:\n%s" % e)

        if not os.path.exists(connection_file):
            if kernel.poll() is None:
                kernel.terminate()
            raise IOError("Connection file %r never arrived" % connection_file)

        client = BlockingKernelClient(connection_file=connection_file)
        tic = time.time()
        while True:
            try:
                client.load_connection_file()
                break
            except ValueError:
                # The file is not written yet
                if time.time() > tic + SETUP_TIMEOUT:
                    # Give up after 5s
                    raise IOError("Kernel failed to write connection file")
        client.start_channels()
        client.wait_for_ready()
        try:
            yield client
        finally:
            client.stop_channels()
    finally:
        kernel.terminate()


class Comm():
    """
    Comm base class, copied from qtconsole without the qt stuff
    """

    def __init__(self, target_name, kernel_client,
                 msg_callback=None, close_callback=None):
        """
        Create a new comm. Must call open to use.
        """
        self.target_name = target_name
        self.kernel_client = kernel_client
        self.comm_id = uuid.uuid1().hex
        self._msg_callback = msg_callback
        self._close_callback = close_callback
        self._send_channel = self.kernel_client.shell_channel

    def _send_msg(self, msg_type, content, data, metadata, buffers):
        """
        Send a message on the shell channel.
        """
        if data is None:
            data = {}
        if content is None:
            content = {}
        content['comm_id'] = self.comm_id
        content['data'] = data
        msg = self.kernel_client.session.msg(
            msg_type, content, metadata=metadata)
        if buffers:
            msg['buffers'] = buffers
        return self._send_channel.send(msg)

    # methods for sending messages
    def open(self, data=None, metadata=None, buffers=None):
        """Open the kernel-side version of this comm"""
        return self._send_msg(
            'comm_open', {'target_name': self.target_name},
            data, metadata, buffers)

    def send(self, data=None, metadata=None, buffers=None):
        """Send a message to the kernel-side version of this comm"""
        return self._send_msg(
            'comm_msg', {}, data, metadata, buffers)

    def close(self, data=None, metadata=None, buffers=None):
        """Close the kernel-side version of this comm"""
        return self._send_msg(
            'comm_close', {}, data, metadata, buffers)

    def on_msg(self, callback):
        """Register a callback for comm_msg

        Will be called with the `data` of any comm_msg messages.

        Call `on_msg(None)` to disable an existing callback.
        """
        self._msg_callback = callback

    def on_close(self, callback):
        """Register a callback for comm_close

        Will be called with the `data` of the close message.

        Call `on_close(None)` to disable an existing callback.
        """
        self._close_callback = callback

    # methods for handling incoming messages
    def handle_msg(self, msg):
        """Handle a comm_msg message"""
        if self._msg_callback:
            return self._msg_callback(msg)

    def handle_close(self, msg):
        """Handle a comm_close message"""
        if self._close_callback:
            return self._close_callback(msg)


# =============================================================================
# Fixtures
# =============================================================================
@pytest.fixture
def kernel(request):
    """Console kernel fixture"""
    # Get kernel instance
    kernel = get_kernel()
    kernel.namespace_view_settings = {
        'check_all': False,
        'exclude_private': True,
        'exclude_uppercase': True,
        'exclude_capitalized': False,
        'exclude_unsupported': False,
        'exclude_callables_and_modules': True,
        'excluded_names': [
            'nan',
            'inf',
            'infty',
            'little_endian',
            'colorbar_doc',
            'typecodes',
            '__builtins__',
            '__main__',
            '__doc__',
            'NaN',
            'Inf',
            'Infinity',
            'sctypes',
            'rcParams',
            'rcParamsDefault',
            'sctypeNA',
            'typeNA',
            'False_',
            'True_'
        ],
        'minmax': False,
        'filter_on': True
    }

    # Teardown
    def reset_kernel():
        asyncio.run(kernel.do_execute('reset -f', True))
    request.addfinalizer(reset_kernel)

    return kernel


# =============================================================================
# Tests
# =============================================================================
def test_magics(kernel):
    """Check available magics in the kernel."""
    line_magics = kernel.shell.magics_manager.magics['line']
    cell_magics = kernel.shell.magics_manager.magics['cell']
    for magic in ['alias', 'alias_magic', 'autocall', 'automagic', 'autosave',
                  'bookmark', 'cd', 'clear', 'colors',
                  'config', 'connect_info', 'debug',
                  'dhist', 'dirs', 'doctest_mode', 'ed', 'edit', 'env',
                  'gui', 'hist', 'history', 'killbgscripts', 'ldir', 'less',
                  'load', 'load_ext', 'loadpy', 'logoff', 'logon', 'logstart',
                  'logstate', 'logstop', 'ls', 'lsmagic', 'macro', 'magic',
                  'matplotlib', 'mkdir', 'more', 'notebook', 'page',
                  'pastebin', 'pdb', 'pdef', 'pdoc', 'pfile', 'pinfo',
                  'pinfo2', 'popd', 'pprint', 'precision', 'prun',
                  'psearch', 'psource', 'pushd', 'pwd', 'pycat', 'pylab',
                  'qtconsole', 'quickref', 'recall', 'rehashx', 'reload_ext',
                  'rep', 'rerun', 'reset', 'reset_selective', 'rmdir',
                  'run', 'save', 'sc', 'set_env', 'sx', 'system',
                  'tb', 'time', 'timeit', 'unalias', 'unload_ext',
                  'who', 'who_ls', 'whos', 'xdel', 'xmode']:
        msg = "magic '%s' is not in line_magics" % magic
        assert magic in line_magics, msg

    for magic in ['!', 'HTML', 'SVG', 'bash', 'capture', 'debug',
                  'file', 'html', 'javascript', 'js', 'latex', 'perl',
                  'prun', 'pypy', 'python', 'python2', 'python3',
                  'ruby', 'script', 'sh', 'svg', 'sx', 'system', 'time',
                  'timeit', 'writefile']:
        assert magic in cell_magics


# --- For the Variable Explorer
def test_get_namespace_view(kernel):
    """
    Test the namespace view of the kernel.
    """
    asyncio.run(kernel.do_execute('a = 1', True))

    nsview = repr(kernel.get_namespace_view())
    assert "'a':" in nsview
    assert "'type': 'int'" in nsview or "'type': u'int'" in nsview
    assert "'size': 1" in nsview
    assert "'view': '1'" in nsview
    assert "'numpy_type': 'Unknown'" in nsview
    assert "'python_type': 'int'" in nsview


@pytest.mark.parametrize("filter_on", [True, False])
def test_get_namespace_view_filter_on(kernel, filter_on):
    """
    Test the namespace view of the kernel with filters on and off.
    """
    asyncio.run(kernel.do_execute('a = 1', True))
    asyncio.run(kernel.do_execute('TestFilterOff = 1', True))

    settings = kernel.namespace_view_settings
    settings['filter_on'] = filter_on
    settings['exclude_capitalized'] = True
    nsview = kernel.get_namespace_view()

    if not filter_on:
        assert 'a' in nsview
        assert 'TestFilterOff' in nsview
    else:
        assert 'TestFilterOff' not in nsview
        assert 'a' in nsview

    # Restore settings for other tests
    settings['filter_on'] = True
    settings['exclude_capitalized'] = False


def test_get_var_properties(kernel):
    """
    Test the properties fo the variables in the namespace.
    """
    asyncio.run(kernel.do_execute('a = 1', True))

    var_properties = repr(kernel.get_var_properties())
    assert "'a'" in var_properties
    assert "'is_list': False" in var_properties
    assert "'is_dict': False" in var_properties
    assert "'len': 1" in var_properties
    assert "'is_array': False" in var_properties
    assert "'is_image': False" in var_properties
    assert "'is_data_frame': False" in var_properties
    assert "'is_series': False" in var_properties
    assert "'array_shape': None" in var_properties
    assert "'array_ndim': None" in var_properties


def test_get_value(kernel):
    """Test getting the value of a variable."""
    name = 'a'
    asyncio.run(kernel.do_execute("a = 124", True))

    # Check data type send
    assert kernel.get_value(name) == 124


def test_get_value_with_polars(kernel):
    """Test getting the value of a Polars DataFrame."""
    import pandas
    from pandas.testing import assert_frame_equal

    command = "import polars; polars_df = polars.DataFrame({'a': [10]})"
    asyncio.run(kernel.do_execute(command, True))
    pandas_df = pandas.DataFrame({'a': [10]})
    assert_frame_equal(kernel.get_value('polars_df'), pandas_df)


def test_set_value(kernel):
    """Test setting the value of a variable."""
    name = 'a'
    asyncio.run(kernel.do_execute('a = 0', True))
    value = 10
    kernel.set_value(name, value)
    log_text = get_log_text(kernel)
    assert "'__builtin__': <module " in log_text
    assert "'__builtins__': <module " in log_text
    assert "'_ih': ['']" in log_text
    assert "'_oh': {}" in log_text
    assert "'a': 10" in log_text


def test_remove_value(kernel):
    """Test the removal of a variable."""
    name = 'a'
    asyncio.run(kernel.do_execute('a = 1', True))

    var_properties = repr(kernel.get_var_properties())
    assert "'a'" in var_properties
    assert "'is_list': False" in var_properties
    assert "'is_dict': False" in var_properties
    assert "'len': 1" in var_properties
    assert "'is_array': False" in var_properties
    assert "'is_image': False" in var_properties
    assert "'is_data_frame': False" in var_properties
    assert "'is_series': False" in var_properties
    assert "'array_shape': None" in var_properties
    assert "'array_ndim': None" in var_properties
    kernel.remove_value(name)
    var_properties = repr(kernel.get_var_properties())
    assert var_properties == '{}'


def test_copy_value(kernel):
    """Test the copy of a variable."""
    orig_name = 'a'
    new_name = 'b'
    asyncio.run(kernel.do_execute('a = 1', True))

    var_properties = repr(kernel.get_var_properties())
    assert "'a'" in var_properties
    assert "'is_list': False" in var_properties
    assert "'is_dict': False" in var_properties
    assert "'len': 1" in var_properties
    assert "'is_array': False" in var_properties
    assert "'is_image': False" in var_properties
    assert "'is_data_frame': False" in var_properties
    assert "'is_series': False" in var_properties
    assert "'array_shape': None" in var_properties
    assert "'array_ndim': None" in var_properties
    kernel.copy_value(orig_name, new_name)
    var_properties = repr(kernel.get_var_properties())
    assert "'a'" in var_properties
    assert "'b'" in var_properties
    assert "'is_list': False" in var_properties
    assert "'is_dict': False" in var_properties
    assert "'len': 1" in var_properties
    assert "'is_array': False" in var_properties
    assert "'is_image': False" in var_properties
    assert "'is_data_frame': False" in var_properties
    assert "'is_series': False" in var_properties
    assert "'array_shape': None" in var_properties
    assert "'array_ndim': None" in var_properties


@pytest.mark.parametrize(
    "load", [(True, "val1 = 0", {"val1": np.array(1)}),
             (False, "val1 = 0", {"val1": 0, "val1_000": np.array(1)})])
def test_load_npz_data(kernel, load):
    """Test loading data from npz filename."""
    namespace_file = osp.join(FILES_PATH, 'load_data.npz')
    extention = '.npz'
    overwrite, execute, variables = load
    asyncio.run(kernel.do_execute(execute, True))

    kernel.load_data(namespace_file, extention, overwrite=overwrite)
    for var, value in variables.items():
        assert value == kernel.get_value(var)


def test_load_data(kernel):
    """Test loading data from filename."""
    namespace_file = osp.join(FILES_PATH, 'load_data.spydata')
    extention = '.spydata'
    kernel.load_data(namespace_file, extention)
    var_properties = repr(kernel.get_var_properties())
    assert "'a'" in var_properties
    assert "'is_list': False" in var_properties
    assert "'is_dict': False" in var_properties
    assert "'len': 1" in var_properties
    assert "'is_array': False" in var_properties
    assert "'is_image': False" in var_properties
    assert "'is_data_frame': False" in var_properties
    assert "'is_series': False" in var_properties
    assert "'array_shape': None" in var_properties
    assert "'array_ndim': None" in var_properties


def test_save_namespace(kernel):
    """Test saving the namespace into filename."""
    namespace_file = osp.join(FILES_PATH, 'save_data.spydata')
    asyncio.run(kernel.do_execute('b = 1', True))

    kernel.save_namespace(namespace_file)
    assert osp.isfile(namespace_file)
    load_func = iofunctions.load_funcs['.spydata']
    data, error_message = load_func(namespace_file)
    assert data == {'b': 1}
    assert not error_message
    os.remove(namespace_file)
    assert not osp.isfile(namespace_file)


# --- For the Help plugin
def test_is_defined(kernel):
    """Test method to tell if object is defined."""
    obj = "debug"
    assert kernel.is_defined(obj)


def test_get_doc(kernel):
    """Test to get object documentation dictionary."""
    objtxt = 'help'
    assert (
        "Define the builtin 'help'" in kernel.get_doc(objtxt)['docstring']
        or "Define the built-in 'help'" in kernel.get_doc(objtxt)['docstring']
    )


def test_get_source(kernel):
    """Test to get object source."""
    objtxt = 'help'
    assert 'class _Helper' in kernel.get_source(objtxt)


# --- Other stuff
@pytest.mark.skipif(os.name == 'nt', reason="Doesn't work on Windows")
def test_output_from_c_libraries(kernel, capsys):
    """Test that the wurlitzer extension is working."""
    # This code was taken from the Wurlitzer demo
    code = """
import ctypes
libc = ctypes.CDLL(None)
libc.printf(('Hello from C\\n').encode('utf8'))
"""

    # With Wurlitzer we have the expected output
    kernel._load_wurlitzer()
    asyncio.run(kernel.do_execute(code, True))
    captured = capsys.readouterr()
    assert captured.out == "Hello from C\n"


@flaky(max_runs=3)
def test_cwd_in_sys_path():
    """
    Test that cwd stays as the first element in sys.path after the
    kernel has started.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        reply = client.execute_interactive(
            "import sys; sys_path = sys.path",
            user_expressions={'output': 'sys_path'}, timeout=TIMEOUT)

        # Transform value obtained through user_expressions
        user_expressions = reply['content']['user_expressions']
        str_value = user_expressions['output']['data']['text/plain']
        value = ast.literal_eval(str_value)

        # Assert the first value of sys_path is an empty string
        assert '' in value


def test_prioritize(kernel):
    """Test that user path priority is honored in sys.path."""
    syspath = kernel.get_syspath()
    append_path = ['/test/append/path']
    prepend_path = ['/test/prepend/path']

    kernel.update_syspath(append_path, prioritize=False)
    new_syspath = kernel.get_syspath()
    assert new_syspath == syspath + append_path

    kernel.update_syspath(prepend_path, prioritize=True)
    new_syspath = kernel.get_syspath()
    assert new_syspath == prepend_path + syspath


@flaky(max_runs=3)
def test_multiprocessing(tmpdir):
    """
    Test that multiprocessing works.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Remove all variables
        client.execute_interactive("%reset -f", timeout=TIMEOUT)

        # Write multiprocessing code to a file
        code = """
from multiprocessing import Pool

def f(x):
    return x*x

if __name__ == '__main__':
    with Pool(5) as p:
        result = p.map(f, [1, 2, 3])
"""
        p = tmpdir.join("mp-test.py")
        p.write(code)

        # Run code
        client.execute_interactive(
            "%runfile {}".format(repr(str(p))), timeout=TIMEOUT)

        # Verify that the `result` variable is defined
        client.inspect('result')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']


@flaky(max_runs=3)
def test_multiprocessing_2(tmpdir):
    """
    Test that multiprocessing works.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Remove all variables
        client.execute_interactive("%reset -f", timeout=TIMEOUT)

        # Write multiprocessing code to a file
        code = """
from multiprocessing import Pool

class myClass():
    def __init__(self, i):
        self.i = i + 10

def myFunc(i):
    return myClass(i)

if __name__ == '__main__':
    with Pool(5) as p:
        result = p.map(myFunc, [1, 2, 3])
    result = [r.i for r in result]
"""
        p = tmpdir.join("mp-test.py")
        p.write(code)

        # Run code
        client.execute_interactive(
            "%runfile {}".format(repr(str(p))), timeout=TIMEOUT)

        # Verify that the `result` variable is defined
        client.inspect('result')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']
        assert "[11, 12, 13]" in content['data']['text/plain']


@flaky(max_runs=3)
@pytest.mark.skipif(
    sys.platform == 'darwin' and sys.version_info[:2] == (3, 8),
    reason="Fails on Mac with Python 3.8")
@pytest.mark.skipif(
    os.environ.get('USE_CONDA') != 'true',
    reason="Doesn't work with pip packages")
def test_dask_multiprocessing(tmpdir):
    """
    Test that dask multiprocessing works.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Remove all variables
        client.execute_interactive("%reset -f")

        # Write multiprocessing code to a file
        # Runs two times to verify that in the second case it doesn't break
        code = """
from dask.distributed import Client

if __name__=='__main__':
    client = Client()
    client.close()
    x = 'hello'
"""
        p = tmpdir.join("mp-test.py")
        p.write(code)

        # Run code two times
        client.execute_interactive(
            "%runfile {}".format(repr(str(p))), timeout=TIMEOUT)

        client.execute_interactive(
            "%runfile {}".format(repr(str(p))), timeout=TIMEOUT)

        # Verify that the `x` variable is defined
        client.inspect('x')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']


@flaky(max_runs=3)
def test_runfile(tmpdir):
    """
    Test that runfile uses the proper name space for execution.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Remove all variables
        client.execute_interactive("%reset -f", timeout=TIMEOUT)

        # Write defined variable code to a file
        code = "result = 'hello world'; error # make an error"
        d = tmpdir.join("defined-test.py")
        d.write(code)

        # Write undefined variable code to a file
        code = dedent("""
        try:
            result3 = result
        except NameError:
            result2 = 'hello world'
        """)
        u = tmpdir.join("undefined-test.py")
        u.write(code)

        # Run code file `d` to define `result` even after an error
        client.execute_interactive(
            "%runfile {}".format(repr(str(d))), timeout=TIMEOUT)

        # Verify that `result` is defined in the current namespace
        client.inspect('result')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']

        # Run code file `u` without current namespace
        client.execute_interactive(
            "%runfile {}".format(repr(str(u))), timeout=TIMEOUT)

        # Verify that the variable `result2` is defined
        client.inspect('result2')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']

        # Run code file `u` with current namespace
        msg = client.execute_interactive(
            "%runfile {} --current-namespace".format(repr(str(u))),
            timeout=TIMEOUT
        )
        content = msg['content']

        # Verify that the variable `result3` is defined
        client.inspect('result3')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']

        # Verify that the variable `__file__` is undefined
        client.inspect('__file__')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert not content['found']


@flaky(max_runs=3)
@pytest.mark.skipif(
    sys.platform == 'darwin' and sys.version_info[:2] == (3, 8),
    reason="Fails on Mac with Python 3.8")
def test_np_threshold(kernel):
    """
    Test that setting Numpy threshold doesn't make the Variable Explorer slow.
    """

    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:

        # Set Numpy threshold, suppress and formatter
        client.execute_interactive("""
import numpy as np;
np.set_printoptions(
    threshold=np.inf,
    suppress=True,
    formatter={'float_kind':'{:0.2f}'.format})
    """, timeout=TIMEOUT)

        # Create a big Numpy array and an array to check decimal format
        client.execute_interactive("""
x = np.random.rand(75000,5);
a = np.array([123412341234.123412341234])
""", timeout=TIMEOUT)

        # Assert that NumPy threshold, suppress and formatter
        # are the same as the ones set by the user
        client.execute_interactive("""
t = np.get_printoptions()['threshold'];
s = np.get_printoptions()['suppress'];
f = np.get_printoptions()['formatter']
""", timeout=TIMEOUT)

        # Check correct decimal format
        client.inspect('a')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "data" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']['data']['text/plain']
        assert "123412341234.12" in content

        # Check threshold value
        client.inspect('t')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "data" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']['data']['text/plain']
        assert "inf" in content

        # Check suppress value
        client.inspect('s')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "data" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']['data']['text/plain']
        assert "True" in content

        # Check formatter
        client.inspect('f')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "data" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']['data']['text/plain']
        assert (
            "{'float_kind': <built-in method format of str object" in content
        )


@flaky(max_runs=3)
@pytest.mark.skipif(
    not TURTLE_ACTIVE,
    reason="Doesn't work on non-interactive settings or Python without Tk")
def test_turtle_launch(tmpdir):
    """Test turtle scripts running in the same kernel."""
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Remove all variables
        client.execute_interactive("%reset -f", timeout=TIMEOUT)

        # Write turtle code to a file
        code = """
import turtle
wn=turtle.Screen()
wn.bgcolor("lightgreen")
tess = turtle.Turtle() # Create tess and set some attributes
tess.color("hotpink")
tess.pensize(5)

tess.forward(80) # Make tess draw equilateral triangle
tess.left(120)
tess.forward(80)
tess.left(120)
tess.forward(80)
tess.left(120) # Complete the triangle

turtle.bye()
"""
        p = tmpdir.join("turtle-test.py")
        p.write(code)

        # Run code
        client.execute_interactive(
            "%runfile {}".format(repr(str(p))), timeout=TIMEOUT)

        # Verify that the `tess` variable is defined
        client.inspect('tess')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']

        # Write turtle code to a file
        code = code + "a = 10"

        p = tmpdir.join("turtle-test1.py")
        p.write(code)

        # Run code again
        client.execute_interactive(
            "%runfile {}".format(repr(str(p))), timeout=TIMEOUT)

        # Verify that the `a` variable is defined
        client.inspect('a')
        msg = client.get_shell_msg(timeout=TIMEOUT)
        while "found" not in msg['content']:
            msg = client.get_shell_msg(timeout=TIMEOUT)
        content = msg['content']
        assert content['found']


@flaky(max_runs=3)
def test_matplotlib_inline(kernel):
    """Test that the default backend for our kernels is 'inline'."""
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Get current backend
        code = "import matplotlib; backend = matplotlib.get_backend()"
        reply = client.execute_interactive(
            code, user_expressions={'output': 'backend'}, timeout=TIMEOUT)

        # Transform value obtained through user_expressions
        user_expressions = reply['content']['user_expressions']
        str_value = user_expressions['output']['data']['text/plain']
        value = ast.literal_eval(str_value)

        # Assert backend is inline
        assert 'inline' in value

@pytest.mark.anyio
async def test_do_complete(kernel):
    """
    Check do complete works in normal and debugging mode.
    """
    await kernel.do_execute("abba = 1", True)
    assert kernel.get_value("abba") == 1
    match = kernel.do_complete("ab", 2)
    if inspect.isawaitable(match):
        match = await match
    assert 'abba' in match['matches']

    # test pdb
    pdb_obj = SpyderPdb()
    pdb_obj.curframe = inspect.currentframe()
    pdb_obj.completenames = lambda *ignore: ['baba']
    kernel.shell._namespace_stack = [pdb_obj]
    match = kernel.do_complete('ba', 2)
    if inspect.isawaitable(match):
        match = await match
    assert 'baba' in match['matches']
    pdb_obj.curframe = None


@pytest.mark.parametrize("exclude_callables_and_modules", [True, False])
@pytest.mark.parametrize("exclude_unsupported", [True, False])
def test_callables_and_modules(kernel, exclude_callables_and_modules,
                               exclude_unsupported):
    """
    Tests that callables and modules are in the namespace view only
    when the right options are passed to the kernel.
    """
    asyncio.run(kernel.do_execute('import numpy', True))
    asyncio.run(kernel.do_execute('a = 10', True))
    asyncio.run(kernel.do_execute('def f(x): return x', True))

    settings = kernel.namespace_view_settings
    settings['exclude_callables_and_modules'] = exclude_callables_and_modules
    settings['exclude_unsupported'] = exclude_unsupported
    nsview = kernel.get_namespace_view()

    # Callables and modules should always be in nsview when the option
    # is active.
    if not exclude_callables_and_modules:
        assert 'numpy' in nsview.keys()
        assert 'f' in nsview.keys()
    else:
        assert 'numpy' not in nsview.keys()
        assert 'f' not in nsview.keys()

    # Other values should always be part of nsview
    assert 'a' in nsview.keys()

    # Restore settings for other tests
    settings['exclude_callables_and_modules'] = True
    settings['exclude_unsupported'] = False


def test_comprehensions_with_locals_in_pdb(kernel):
    """
    Test that evaluating comprehensions with locals works in Pdb.

    Also test that we use the right frame globals, in case the user
    wants to work with them.

    This is a regression test for spyder-ide/spyder#13909.
    """
    pdb_obj = SpyderPdb()
    pdb_obj.curframe = inspect.currentframe()
    pdb_obj.curframe_locals = pdb_obj.curframe.f_locals
    kernel.shell._namespace_stack = [pdb_obj]

    # Create a local variable.
    kernel.shell.pdb_session.default('zz = 10')
    assert kernel.get_value('zz') == 10

    # Run a list comprehension with this variable.
    kernel.shell.pdb_session.default("compr = [zz * i for i in [1, 2, 3]]")
    assert kernel.get_value('compr') == [10, 20, 30]

    # Check that the variable is not reported as being part of globals.
    kernel.shell.pdb_session.default("in_globals = 'zz' in globals()")
    assert kernel.get_value('in_globals') is False

    pdb_obj.curframe = None
    pdb_obj.curframe_locals = None


def test_comprehensions_with_locals_in_pdb_2(kernel):
    """
    Test that evaluating comprehensions with locals works in Pdb.

    This is a regression test for spyder-ide/spyder#16790.
    """
    pdb_obj = SpyderPdb()
    pdb_obj.curframe = inspect.currentframe()
    pdb_obj.curframe_locals = pdb_obj.curframe.f_locals
    kernel.shell._namespace_stack = [pdb_obj]

    # Create a local variable.
    kernel.shell.pdb_session.default('aa = [1, 2]')
    kernel.shell.pdb_session.default('bb = [3, 4]')
    kernel.shell.pdb_session.default('res = []')

    # Run a list comprehension with this variable.
    kernel.shell.pdb_session.default(
        "for c0 in aa: res.append([(c0, c1) for c1 in bb])")
    assert kernel.get_value('res') == [[(1, 3), (1, 4)], [(2, 3), (2, 4)]]

    pdb_obj.curframe = None
    pdb_obj.curframe_locals = None


def test_namespaces_in_pdb(kernel):
    """
    Test namespaces in pdb
    """
    # Define get_ipython for timeit
    get_ipython = lambda: kernel.shell  # noqa
    kernel.shell.user_ns["test"] = 0
    pdb_obj = SpyderPdb()
    pdb_obj.curframe = inspect.currentframe()
    pdb_obj.curframe_locals = pdb_obj.curframe.f_locals
    kernel.shell._namespace_stack = [pdb_obj]

    # Check adding something to globals works
    pdb_obj.default("globals()['test2'] = 0")
    assert pdb_obj.curframe.f_globals["test2"] == 0

    # Create wrapper to check for errors
    old_error = pdb_obj.error
    pdb_obj._error_occured = False

    def error_wrapper(*args, **kwargs):
        print(args, kwargs)
        pdb_obj._error_occured = True
        return old_error(*args, **kwargs)
    pdb_obj.error = error_wrapper

    # Test globals are visible
    pdb_obj.curframe.f_globals["test3"] = 0
    pdb_obj.default("%timeit test3")
    assert not pdb_obj._error_occured

    # Test locals are visible
    pdb_obj.curframe_locals["test4"] = 0
    pdb_obj.default("%timeit test4")
    assert not pdb_obj._error_occured

    # Test user namespace is not visible
    pdb_obj.default("%timeit test")
    assert pdb_obj._error_occured

    pdb_obj.curframe = None
    pdb_obj.curframe_locals = None


def test_functions_with_locals_in_pdb(kernel):
    """
    Test that functions with locals work in Pdb.

    This is a regression test for spyder-ide/spyder-kernels#345
    """
    pdb_obj = SpyderPdb()
    Frame = namedtuple("Frame", ["f_globals"])
    pdb_obj.curframe = Frame(f_globals=kernel.shell.user_ns)
    pdb_obj.curframe_locals = kernel.shell.user_ns
    kernel.shell._namespace_stack = [pdb_obj]

    # Create a local function.
    kernel.shell.pdb_session.default(
        'def fun_a(): return [i for i in range(1)]')
    kernel.shell.pdb_session.default(
        'zz = fun_a()')
    assert kernel.get_value('zz') == [0]

    kernel.shell.pdb_session.default(
        'a = 1')
    kernel.shell.pdb_session.default(
        'def fun_a(): return a')
    kernel.shell.pdb_session.default(
        'zz = fun_a()')
    assert kernel.get_value('zz') == 1

    pdb_obj.curframe = None
    pdb_obj.curframe_locals = None


def test_functions_with_locals_in_pdb_2(kernel):
    """
    Test that functions with locals work in Pdb.

    This is another regression test for spyder-ide/spyder-kernels#345
    """
    baba = 1  # noqa
    pdb_obj = SpyderPdb()
    pdb_obj.curframe = inspect.currentframe()
    pdb_obj.curframe_locals = pdb_obj.curframe.f_locals
    kernel.shell._namespace_stack = [pdb_obj]

    # Create a local function.
    kernel.shell.pdb_session.default(
        'def fun_a(): return [i for i in range(1)]')
    kernel.shell.pdb_session.default(
        'zz = fun_a()')
    assert kernel.get_value('zz') == [0]

    kernel.shell.pdb_session.default(
        'a = 1')
    kernel.shell.pdb_session.default(
        'def fun_a(): return a')
    kernel.shell.pdb_session.default(
        'zz = fun_a()')
    assert kernel.get_value('zz') == 1

    # Check baba is in locals and not globals
    kernel.shell.pdb_session.default(
        'll = locals().keys()')
    assert "baba" in kernel.get_value('ll')
    kernel.shell.pdb_session.default(
        'gg = globals().keys()')
    assert "baba" not in kernel.get_value('gg')

    pdb_obj.curframe = None
    pdb_obj.curframe_locals = None


def test_locals_globals_in_pdb(kernel):
    """
    Test thal locals and globals work properly in Pdb.
    """
    a = 1  # noqa
    pdb_obj = SpyderPdb()
    pdb_obj.curframe = inspect.currentframe()
    pdb_obj.curframe_locals = pdb_obj.curframe.f_locals
    kernel.shell._namespace_stack = [pdb_obj]

    assert kernel.get_value('a') == 1

    kernel.shell.pdb_session.default(
        'test = "a" in globals()')
    assert kernel.get_value('test') is False

    kernel.shell.pdb_session.default(
        'test = "a" in locals()')
    assert kernel.get_value('test') is True

    kernel.shell.pdb_session.default(
        'def f(): return a')
    kernel.shell.pdb_session.default(
        'test = f()')
    assert kernel.get_value('test') == 1

    kernel.shell.pdb_session.default(
        'a = 2')
    assert kernel.get_value('a') == 2

    kernel.shell.pdb_session.default(
        'test = "a" in globals()')
    assert kernel.get_value('test') is False

    kernel.shell.pdb_session.default(
        'test = "a" in locals()')
    assert kernel.get_value('test') is True

    pdb_obj.curframe = None
    pdb_obj.curframe_locals = None


@flaky(max_runs=3)
@pytest.mark.parametrize("backend", [None, 'inline', 'tk', 'qt'])
@pytest.mark.skipif(
    os.environ.get('USE_CONDA') != 'true',
    reason="Doesn't work with pip packages"
)
def test_get_interactive_backend(backend):
    """
    Test that we correctly get the interactive backend set in the kernel.
    """
    # This test passes locally but fails on CIs. Don't know why.
    if sys.platform == "darwin" and backend == "qt" and os.environ.get('CI'):
        return

    cmd = "from spyder_kernels.console import start; start.main()"
    with setup_kernel(cmd) as client:
        # Set backend
        if backend is not None:
            client.execute_interactive(
                "%matplotlib {}".format(backend), timeout=TIMEOUT
            )
            client.execute_interactive(
                "import time; time.sleep(.1)", timeout=TIMEOUT
            )

        # Get backend
        code = "backend = get_ipython().kernel.get_mpl_interactive_backend()"
        reply = client.execute_interactive(
            code, user_expressions={'output': 'backend'}, timeout=TIMEOUT
        )

        # Get value obtained through user_expressions
        user_expressions = reply['content']['user_expressions']
        value = user_expressions['output']['data']['text/plain']

        # remove quotes
        value = value[1:-1]

        # Assert we got the right interactive backend
        if backend is not None:
            assert value == backend
        else:
            assert value == 'inline'


def test_global_message(tmpdir):
    """
    Test that using `global` triggers a warning.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Remove all variables
        client.execute_interactive("%reset -f", timeout=TIMEOUT)

        # Write code with a global to a file
        code = (
            "def foo1():\n"
            "    global x\n"
            "    x = 2\n"
            "x = 1\n"
            "print(x)\n"
        )

        p = tmpdir.join("test.py")
        p.write(code)
        global found
        found = False

        def check_found(msg):
            if "text" in msg["content"]:
                if ("WARNING: This file contains a global statement" in
                        msg["content"]["text"]):
                    global found
                    found = True

        # Run code in current namespace
        client.execute_interactive("%runfile {} --current-namespace".format(
            repr(str(p))), timeout=TIMEOUT, output_hook=check_found)
        assert not found

        # Run code in empty namespace
        client.execute_interactive(
            "%runfile {}".format(repr(str(p))), timeout=TIMEOUT,
            output_hook=check_found)

        assert found


@flaky(max_runs=3)
def test_debug_namespace(tmpdir):
    """
    Test that the kernel uses the proper namespace while debugging.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"

    with setup_kernel(cmd) as client:
        # Write code to a file
        d = tmpdir.join("pdb-ns-test.py")
        d.write('def func():\n    bb = "hello"\n    breakpoint()\nfunc()')

        # Run code file `d`
        client.execute("%runfile {}".format(repr(str(d))))

        # make sure that 'bb' returns 'hello'
        client.get_stdin_msg(timeout=TIMEOUT)
        client.input('bb')

        t0 = time.time()
        while True:
            assert time.time() - t0 < 5
            msg = client.get_iopub_msg(timeout=TIMEOUT)
            if msg.get('msg_type') == 'stream':
                if 'hello' in msg["content"].get("text"):
                    break

        # make sure that get_value('bb') returns 'hello'
        client.get_stdin_msg(timeout=TIMEOUT)
        client.input("get_ipython().kernel.get_value('bb')")

        t0 = time.time()
        while True:
            assert time.time() - t0 < 5
            msg = client.get_iopub_msg(timeout=TIMEOUT)
            if msg.get('msg_type') == 'stream':
                if 'hello' in msg["content"].get("text"):
                    break


def test_interrupt_short_loop():
    """
    Test that the kernel can be interrupted by calling a comm handler.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"
    with setup_kernel(cmd) as client:
        kernel_comm = CommBase()

        # Create new comm and send the highest protocol
        comm = Comm(kernel_comm._comm_name, client)
        comm.open(data={})
        comm._send_channel = client.control_channel
        kernel_comm._register_comm(comm)

        client.execute_interactive("import time", timeout=TIMEOUT)

        # Try interrupting loop
        t0 = time.time()
        msg_id = client.execute("for i in range(100): time.sleep(.1)")
        time.sleep(.2)
        # Raise interrupt on control_channel
        kernel_comm.remote_call().raise_interrupt_signal()
        # Wait for shell message
        while True:
            delta = time.time() - t0
            assert delta < 5
            msg = client.get_shell_msg(timeout=TIMEOUT)
            if msg["parent_header"].get("msg_id") != msg_id:
                # not from my request
                continue
            break
        delta = time.time() - t0
        assert delta < 5, (
            "10 seconds long call should have been interrupted, so the "
            "interrupt signal was likely mishandled"
        )


@pytest.mark.skipif(os.name == "nt", reason="Windows doesn't do 'interrupting sleep'")
def test_interrupt_long_sleep():
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"
    with setup_kernel(cmd) as client:
        kernel_comm = CommBase()

        # Create new comm and send the highest protocol
        comm = Comm(kernel_comm._comm_name, client)
        comm.open(data={})
        comm._send_channel = client.control_channel
        kernel_comm._register_comm(comm)

        client.execute_interactive("import time", timeout=TIMEOUT)


        # Try interrupting sleep
        t0 = time.time()
        msg_id = client.execute("time.sleep(10)")
        time.sleep(.2)
        # Raise interrupt on control_channel
        kernel_comm.remote_call().raise_interrupt_signal()
        # Wait for shell message
        while True:
            delta = time.time() - t0
            assert delta < 5
            msg = client.get_shell_msg(timeout=TIMEOUT)
            if msg["parent_header"].get("msg_id") != msg_id:
                # not from my request
                continue
            break

        delta = time.time() - t0
        assert delta < 5, (
            "10 seconds long call should have been interrupted, so the "
            "interrupt signal was likely mishandled"
        )


def test_enter_debug_after_interruption():
    """
    Test that we can enter the debugger after interrupting the current
    execution.
    """
    # Command to start the kernel
    cmd = "from spyder_kernels.console import start; start.main()"
    with setup_kernel(cmd) as client:
        kernel_comm = CommBase()

        # Create new comm and send the highest protocol
        comm = Comm(kernel_comm._comm_name, client)
        comm.open(data={})
        comm._send_channel = client.control_channel
        kernel_comm._register_comm(comm)

        client.execute_interactive("import time", timeout=TIMEOUT)

        # Try interrupting loop
        t0 = time.time()
        msg_id = client.execute("for i in range(100): time.sleep(.1)")
        time.sleep(.2)
        # Request to enter the debugger
        kernel_comm.remote_call().request_pdb_stop()
        # Wait for debug message
        while True:
            assert time.time() - t0 < 5
            msg = client.get_iopub_msg(timeout=TIMEOUT)
            if msg.get('msg_type') == 'stream':
                print(msg["content"].get("text"))
            if msg["parent_header"].get("msg_id") != msg_id:
                # not from my request
                continue
            if msg.get('msg_type') == 'comm_msg':
                if msg["content"].get("data", {}).get("content", {}).get(
                        'call_name') == 'pdb_input':
                    # pdb entered
                    break
                comm.handle_msg(msg)

        assert time.time() - t0 < 5


def test_non_strings_in_locals(kernel):
    """
    Test that we can hande non-string entries in `locals` when bulding the
    namespace view.

    This is a regression test for issue spyder-ide/spyder#19145
    """
    asyncio.run(kernel.do_execute('locals().update({1:2})', True))
    nsview = repr(kernel.get_namespace_view())
    assert "1:" in nsview


def test_django_settings(kernel):
    """
    Test that we don't generate errors when importing `django.conf.settings`.

    This is a regression test for issue spyder-ide/spyder#19516
    """
    import django
    asyncio.run(kernel.do_execute('from django.conf import settings', True))
    nsview = repr(kernel.get_namespace_view())
    assert "'settings':" in nsview


def test_hard_link_pdb(tmpdir):
    """
    Test that breakpoints on a file are recognised even when the path is
    different.
    """
    # Create a file and a hard link
    d = tmpdir.join("file.py")
    d.write('def func():\n    bb = "hello"\n')
    folder = tmpdir.join("folder")
    os.mkdir(folder)
    hard_link = folder.join("file.py")
    os.link(d, hard_link)

    # Make sure both paths point to the same file
    assert os.path.samefile(d, hard_link)

    # Make sure canonic returns the same path for a single file
    pdb_obj = SpyderPdb()
    assert pdb_obj.canonic(str(d)) == pdb_obj.canonic(str(hard_link))


@pytest.mark.skipif(not os.environ.get('CI'), reason="Only works on CIs")
def test_get_pythonenv_info(kernel):
    """Test the output we get from this method."""
    output = kernel.get_pythonenv_info()
    assert output["path"] == sys.executable

    if os.environ.get('USE_CONDA'):
        assert output["name"] == "test"
        assert output["env_type"] == PythonEnvType.Conda
    else:
        assert output["env_type"] in [
            # This Custom here accounts for Linux packagers that run our tests
            # in their CIs
            PythonEnvType.Custom,
            PythonEnvType.Conda,
        ]

    # Check these keys are present. Otherwise we'll break Spyder.
    assert output["python_version"] == sys.version.split()[0]
    assert output["ipython_version"] == ipython_release.version
    assert output["sys_version"] == sys.version


@pytest.mark.parametrize("prefix", ["%", "!"])
def test_disable_pkg_managers(kernel, capsys, prefix):
    """Test that we disable Python package manager magics and commands."""
    pkg_manager = random.choice(kernel.shell._disabled_pkg_managers)
    asyncio.run(kernel.do_execute(f"{prefix}{pkg_manager}", True))
    captured = capsys.readouterr()
    assert kernel.shell._disable_pkg_managers_msg[2:] == captured.out[1:-1]


if __name__ == "__main__":
    pytest.main()
