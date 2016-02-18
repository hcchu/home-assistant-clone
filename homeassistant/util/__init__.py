"""
homeassistant.util
~~~~~~~~~~~~~~~~~~

Helper methods for various modules.
"""
import collections
from itertools import chain
import threading
import queue
from datetime import datetime
import re
import enum
import socket
import random
import string
from functools import wraps
from types import MappingProxyType

from .dt import datetime_to_local_str, utcnow

RE_SANITIZE_FILENAME = re.compile(r'(~|\.\.|/|\\)')
RE_SANITIZE_PATH = re.compile(r'(~|\.(\.)+)')
RE_SLUGIFY = re.compile(r'[^a-z0-9_]+')


def sanitize_filename(filename):
    """ Sanitizes a filename by removing .. / and \\. """
    return RE_SANITIZE_FILENAME.sub("", filename)


def sanitize_path(path):
    """ Sanitizes a path by removing ~ and .. """
    return RE_SANITIZE_PATH.sub("", path)


def slugify(text):
    """ Slugifies a given text. """
    text = text.lower().replace(" ", "_")

    return RE_SLUGIFY.sub("", text)


def repr_helper(inp):
    """ Helps creating a more readable string representation of objects. """
    if isinstance(inp, (dict, MappingProxyType)):
        return ", ".join(
            repr_helper(key)+"="+repr_helper(item) for key, item
            in inp.items())
    elif isinstance(inp, datetime):
        return datetime_to_local_str(inp)
    else:
        return str(inp)


def convert(value, to_type, default=None):
    """ Converts value to to_type, returns default if fails. """
    try:
        return default if value is None else to_type(value)
    except ValueError:
        # If value could not be converted
        return default


def ensure_unique_string(preferred_string, current_strings):
    """ Returns a string that is not present in current_strings.
        If preferred string exists will append _2, _3, .. """
    test_string = preferred_string
    current_strings = set(current_strings)

    tries = 1

    while test_string in current_strings:
        tries += 1
        test_string = "{}_{}".format(preferred_string, tries)

    return test_string


# Taken from: http://stackoverflow.com/a/11735897
def get_local_ip():
    """ Tries to determine the local IP address of the machine. """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Use Google Public DNS server to determine own IP
        sock.connect(('8.8.8.8', 80))

        return sock.getsockname()[0]
    except socket.error:
        return socket.gethostbyname(socket.gethostname())
    finally:
        sock.close()


# Taken from http://stackoverflow.com/a/23728630
def get_random_string(length=10):
    """ Returns a random string with letters and digits. """
    generator = random.SystemRandom()
    source_chars = string.ascii_letters + string.digits

    return ''.join(generator.choice(source_chars) for _ in range(length))


class OrderedEnum(enum.Enum):
    """ Taken from Python 3.4.0 docs. """
    # pylint: disable=no-init, too-few-public-methods

    def __ge__(self, other):
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __gt__(self, other):
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __le__(self, other):
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented


class OrderedSet(collections.MutableSet):
    """ Ordered set taken from http://code.activestate.com/recipes/576694/ """

    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        """ Add an element to the end of the set. """
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def promote(self, key):
        """ Promote element to beginning of the set, add if not there. """
        if key in self.map:
            self.discard(key)

        begin = self.end[2]
        curr = begin[1]
        curr[2] = begin[1] = self.map[key] = [key, curr, begin]

    def discard(self, key):
        """ Discard an element from the set. """
        if key in self.map:
            key, prev_item, next_item = self.map.pop(key)
            prev_item[2] = next_item
            next_item[1] = prev_item

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):  # pylint: disable=arguments-differ
        """
        Pops element of the end of the set.
        Set last=False to pop from the beginning.
        """
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def update(self, *args):
        """ Add elements from args to the set. """
        for item in chain(*args):
            self.add(item)

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


class Throttle(object):
    """
    A method decorator to add a cooldown to a method to prevent it from being
    called more then 1 time within the timedelta interval `min_time` after it
    returned its result.

    Calling a method a second time during the interval will return None.

    Pass keyword argument `no_throttle=True` to the wrapped method to make
    the call not throttled.

    Decorator takes in an optional second timedelta interval to throttle the
    'no_throttle' calls.

    Adds a datetime attribute `last_call` to the method.
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, min_time, limit_no_throttle=None):
        self.min_time = min_time
        self.limit_no_throttle = limit_no_throttle

    def __call__(self, method):
        if self.limit_no_throttle is not None:
            method = Throttle(self.limit_no_throttle)(method)

        # Different methods that can be passed in:
        #  - a function
        #  - an unbound function on a class
        #  - a method (bound function on a class)

        # We want to be able to differentiate between function and unbound
        # methods (which are considered functions).
        # All methods have the classname in their qualname seperated by a '.'
        # Functions have a '.' in their qualname if defined inline, but will
        # be prefixed by '.<locals>.' so we strip that out.
        is_func = (not hasattr(method, '__self__') and
                   '.' not in method.__qualname__.split('.<locals>.')[-1])

        @wraps(method)
        def wrapper(*args, **kwargs):
            """
            Wrapper that allows wrapped to be called only once per min_time.
            If we cannot acquire the lock, it is running so return None.
            """
            # pylint: disable=protected-access
            if hasattr(method, '__self__'):
                host = method.__self__
            elif is_func:
                host = wrapper
            else:
                host = args[0] if args else wrapper

            if not hasattr(host, '_throttle_lock'):
                host._throttle_lock = threading.Lock()

            if not host._throttle_lock.acquire(False):
                return None

            last_call = getattr(host, '_throttle_last_call', None)
            # Check if method is never called or no_throttle is given
            force = not last_call or kwargs.pop('no_throttle', False)

            try:
                if force or utcnow() - last_call > self.min_time:
                    result = method(*args, **kwargs)
                    host._throttle_last_call = utcnow()
                    return result
                else:
                    return None
            finally:
                host._throttle_lock.release()

        return wrapper


class ThreadPool(object):
    """A priority queue-based thread pool."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, job_handler, worker_count=0, busy_callback=None):
        """
        job_handler: method to be called from worker thread to handle job
        worker_count: number of threads to run that handle jobs
        busy_callback: method to be called when queue gets too big.
                       Parameters: worker_count, list of current_jobs,
                                   pending_jobs_count
        """
        self._job_handler = job_handler
        self._busy_callback = busy_callback

        self.worker_count = 0
        self.busy_warning_limit = 0
        self._work_queue = queue.PriorityQueue()
        self.current_jobs = []
        self._lock = threading.RLock()
        self._quit_task = object()

        self.running = True

        for _ in range(worker_count):
            self.add_worker()

    def add_worker(self):
        """Add worker to the thread pool and reset warning limit."""
        with self._lock:
            if not self.running:
                raise RuntimeError("ThreadPool not running")

            worker = threading.Thread(target=self._worker)
            worker.daemon = True
            worker.start()

            self.worker_count += 1
            self.busy_warning_limit = self.worker_count * 3

    def remove_worker(self):
        """Remove worker from the thread pool and reset warning limit."""
        with self._lock:
            if not self.running:
                raise RuntimeError("ThreadPool not running")

            self._work_queue.put(PriorityQueueItem(0, self._quit_task))

            self.worker_count -= 1
            self.busy_warning_limit = self.worker_count * 3

    def add_job(self, priority, job):
        """ Add a job to the queue. """
        with self._lock:
            if not self.running:
                raise RuntimeError("ThreadPool not running")

            self._work_queue.put(PriorityQueueItem(priority, job))

            # check if our queue is getting too big
            if self._work_queue.qsize() > self.busy_warning_limit \
               and self._busy_callback is not None:

                # Increase limit we will issue next warning
                self.busy_warning_limit *= 2

                self._busy_callback(
                    self.worker_count, self.current_jobs,
                    self._work_queue.qsize())

    def block_till_done(self):
        """Block till current work is done."""
        self._work_queue.join()
        # import traceback
        # traceback.print_stack()

    def stop(self):
        """Finish all the jobs and stops all the threads."""
        self.block_till_done()

        with self._lock:
            if not self.running:
                return

            # Tell the workers to quit
            for _ in range(self.worker_count):
                self.remove_worker()

            self.running = False

            # Wait till all workers have quit
            self.block_till_done()

    def _worker(self):
        """Handle jobs for the thread pool."""
        while True:
            # Get new item from work_queue
            job = self._work_queue.get().item

            if job == self._quit_task:
                self._work_queue.task_done()
                return

            # Add to current running jobs
            job_log = (utcnow(), job)
            self.current_jobs.append(job_log)

            # Do the job
            self._job_handler(job)

            # Remove from current running job
            self.current_jobs.remove(job_log)

            # Tell work_queue the task is done
            self._work_queue.task_done()


class PriorityQueueItem(object):
    """ Holds a priority and a value. Used within PriorityQueue. """

    # pylint: disable=too-few-public-methods
    def __init__(self, priority, item):
        self.priority = priority
        self.item = item

    def __lt__(self, other):
        return self.priority < other.priority
