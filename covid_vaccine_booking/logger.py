import os
import logging
import logging.config
import logging.handlers
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


def start_thread_logging():
    """
    Add a log handler to separate file for current thread
    """
    thread_name = threading.Thread.getName(threading.current_thread())
    log_file = '/tmp/perThreadLogging-{}.log'.format(thread_name)
    log_handler = logging.FileHandler(log_file)

    log_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)-15s"
        "| %(threadName)-11s"
        "| %(levelname)-5s"
        "| %(message)s")
    log_handler.setFormatter(formatter)

    log_filter = ThreadLogFilter(thread_name)
    log_handler.addFilter(log_filter)

    logger = logging.getLogger()
    logger.addHandler(log_handler)

    return log_handler


def stop_thread_logging(log_handler):
    # Remove thread log handler from root logger
    logging.getLogger().removeHandler(log_handler)

    # Close the thread log handler so that the lock on log file can be released
    log_handler.close()



def config_root_logger():
    log_file = '/tmp/perThreadLogging.log'

    formatter = "%(asctime)-15s" \
                "| %(threadName)-11s" \
                "| %(levelname)-5s" \
                "| %(message)s"

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'root_formatter': {
                'format': formatter
            }
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'root_formatter'
            },
            'log_file': {
                'class': 'logging.FileHandler',
                'level': 'DEBUG',
                'filename': log_file,
                'formatter': 'root_formatter',
            }
        },
        'loggers': {
            '': {
                'handlers': [
                    'console',
                    'log_file',
                ],
                'level': 'DEBUG',
                'propagate': True
            }
        }
    })



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
            'format': '%(asctime)s [%(threadName)s] [%(name)s] [%(levelname)s] %(message)s    %(pathname)s:%(lineno)s(%(funcName)s)',
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
    },
    'handlers': {
        'console': {
            'formatter': 'minimal_colered',
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'filehandler': {
            'formatter': 'detail',
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, '{}.log'.format(datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))),
        },
    },
    'loggers': {
        'urllib3': {
            'level': 'WARNING',
            'handlers': ['console', 'filehandler'],
            'propagate': False,
        },
        'covid_vaccine_booking': {
            'level': 'INFO',
            'handlers': ['console', 'filehandler'],
            'propagate': False,
        },
        '': {
            'level': 'WARNING',
            'handlers': ['console', 'filehandler'],
            'propagate': False,
        },

    }
})

log = logging.getLogger('covid_vaccine_booking')