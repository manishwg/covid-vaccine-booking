import os
import logging
import logging.config
import logging.handlers
from rich.logging import RichHandler
from  logging import StreamHandler
from logging.handlers import SocketHandler
from datetime import datetime

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


# LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_DIR = '../tmp/logs'

# print ('log dir: ', LOG_DIR)


import threading
import logging
import logging.config


class ThreadLogFilter(logging.Filter):
    """
    This filter only show log entries for specified thread name
    """

    def __init__(self, thread_name, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.thread_name = thread_name

    def filter(self, record):
        return record.threadName == self.thread_name


from rich.console import Console
# error_console = Console(stderr=True)
error_console = Console(stderr=True, style="bold red")

# load config from file
# logging.config.fileConfig('logging.ini', disable_existing_loggers=False)
# or, for dictConfig
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s [%(name)s] [%(levelname)-8s] %(message)s',
        },
        'minimal_colered': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(asctime)-15s| %(name)-22s | %(threadName)-10s | %(log_color)s%(levelname)-6s %(reset)s | %(message)s',
            'log_colors': {
                'DEBUG':    'bold_cyan',
                'INFO':     'bold_green',
                'WARNING':  'bold_yellow',
                'ERROR':    'bold_red',
                'CRITICAL': 'bold_red',
            },
        },
        'detail': {
            'format': '%(asctime)s [%(name)s] [%(levelname)s] %(message)s        (%(funcName)s):%(lineno)s',
        },
        'detail_colered': {
            '()': 'colorlog.ColoredFormatter',
            'format': '%(asctime)s [%(threadName)s] [%(name)s] %(log_color)s[%(levelname)s]  %(reset)s %(message)s    %(purple)s %(pathname)s:%(lineno)s(%(funcName)s)%(thin_white)s',
            'log_colors': {
                'DEBUG':    'bold_cyan',
                'INFO':     'bold_green',
                'WARNING':  'bold_yellow',
                'ERROR':    'bold_red',
                'CRITICAL': 'bold_red',
            },
        },
        'rich_formatter': {
            'format': "%(message)s",
        }

    },
    'filters': {
        'main_thread_filter': {
            '()': ThreadLogFilter,
            'thread_name': 'MainThread',
        },
        'auth_thread_filter': {
            '()': ThreadLogFilter,
            'thread_name': 'AuthThread',
        },
    },
    'handlers': {
        'console': {
            'formatter': 'minimal_colered',
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'main_thread_console': {
            'formatter': 'minimal_colered',
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'filters': ['main_thread_filter',],
        },
        'auth_thread_console': {
            'formatter': 'minimal_colered',
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'filters': ['auth_thread_filter',],
        },
        'rich_console': {
            'formatter': 'rich_formatter',
            'level': 'NOTSET',
            # 'datefmt': "[%X]",
            'class': 'rich.logging.RichHandler',
            'filters': ['main_thread_filter',],
        },
        'filehandler': {
            'formatter': 'detail',
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, '{}.log'.format(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))),
        },
        'main_thread_filehandler': {
            'formatter': 'detail',
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            # 'filename': os.path.join(LOG_DIR, 'main_thread_{}.log'.format(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))),
            'filename': os.path.join(LOG_DIR, 'main_thread_{}.log'),
            'filters': ['main_thread_filter',],
        },
        'auth_thread_filehandler': {
            'formatter': 'detail',
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            # 'filename': os.path.join(LOG_DIR, 'auth_thread_{}.log'.format(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))),
            'filename': os.path.join(LOG_DIR, 'auth_thread.log'),
            'filters': ['auth_thread_filter',],
        },
        'cutelog': {
            'formatter': 'detail',
            'level': 'DEBUG',
            'class': 'logging.handlers.SocketHandler',
            'host': '127.0.0.1',
            'port': '19996',
        },
    },
    'loggers': {
        'urllib3': {
            'level': 'WARNING',
            'handlers': ['cutelog', 'main_thread_filehandler', 'auth_thread_filehandler'],
            'propagate': False,
        },
        'covid_vaccine_booking': {
            'level': 'DEBUG',
            'handlers': ['cutelog', 'main_thread_filehandler', 'auth_thread_filehandler'],
            'propagate': False,
        },
        '': {
            'level': 'WARNING',
            'handlers': ['console', 'filehandler'],
            'propagate': False,
        },

    }
})

# FORMAT = "%(message)s"
# logging.basicConfig(
#     level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
# )

log = logging.getLogger('covid_vaccine_booking')