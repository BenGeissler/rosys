import asyncio
import logging
import shlex
import subprocess
import uuid
from asyncio.subprocess import Process
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from typing import Callable, Optional, Union

from .helpers import is_test

process_pool = ProcessPoolExecutor()
thread_pool = ThreadPoolExecutor(thread_name_prefix='run.py thread_pool')
# NOTE is used in rosys.test.Runtime to advance time slower until computation is done
running_cpu_bound_processes: list[int] = []
running_sh_processes: list[Process] = []
log = logging.getLogger('rosys.run')


async def io_bound(callback: Callable, *args: any):
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(thread_pool, callback, *args)
    except RuntimeError as e:
        if 'cannot schedule new futures after shutdown' not in str(e):
            raise
    except asyncio.exceptions.CancelledError:
        pass


async def cpu_bound(callback: Callable, *args: any):
    with cpu():
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(process_pool, callback, *args)
        except RuntimeError as e:
            if 'cannot schedule new futures after shutdown' not in str(e):
                raise
        except asyncio.exceptions.CancelledError:
            pass


@contextmanager
def cpu():
    id = str(uuid.uuid4())
    running_cpu_bound_processes.append(id)
    try:
        yield
    finally:
        running_cpu_bound_processes.remove(id)


async def sh(command: Union[list[str], str], timeout: Optional[float] = 1, shell=False) -> str:
    '''executes a shell command
    command: a sequence of program arguments as subprocess.Popen requires or full string
    shell: weather a sub shell should be launched (default is False, for speed, use True if you need file globbing or other features);
    returns: stdout
    '''
    command_list = shlex.split(command) if isinstance(command, str) else command
    if timeout is not None:
        command_list = ['timeout', str(timeout)] + command_list

    ic(command_list)

    def popen() -> str:
        with subprocess.Popen(
            ' '.join(command_list) if shell else command_list,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            shell=shell,
        ) as proc:
            stdout, *_ = proc.communicate()
            return stdout.decode('utf-8')
    return await io_bound(popen)


def tear_down() -> None:
    log.info('teardown thread_pool')
    thread_pool.shutdown(wait=False, cancel_futures=True)
    [p.kill() for p in running_sh_processes]
    if not is_test:
        log.info('teardown process_pool')
        [p.kill() for p in process_pool._processes.values()]
        process_pool.shutdown(wait=True, cancel_futures=True)
    log.info('teardown complete')
