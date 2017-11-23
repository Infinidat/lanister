from __future__ import absolute_import

import functools
import os
import sys

import logging
import logging.handlers
import logbook

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger
from celery.log import redirect_stdouts_to_logger
from celery.schedules import crontab

from .app import create_app

_logger = logbook.Logger(__name__)


queue = Celery('tasks', broker='redis://localhost')
queue.conf.update(
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],  # Ignore other content
    CELERY_RESULT_SERIALIZER='json',
    CELERY_ENABLE_UTC=True,
    CELERYBEAT_SCHEDULE={
        'refresh': {
            'task': 'flask_app.tasks.refresh',
            'schedule': crontab(minute='*/10'),
        },
    },
    CELERY_TIMEZONE='UTC'
)

def setup_log(**args):
    logbook.SyslogHandler().push_application()
    logbook.StreamHandler(sys.stderr, bubble=True).push_application()
    redirect_stdouts_to_logger(args['logger']) # logs to local syslog
    if os.path.exists('/dev/log'):
        h = logging.handlers.SysLogHandler('/dev/log')
    else:
        h = logging.handlers.SysLogHandler()
    h.setLevel(args['loglevel'])
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    h.setFormatter(formatter)
    args['logger'].addHandler(h)

APP = None

def needs_app_context(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        global APP

        if APP is None:
            APP = create_app()

        with APP.app_context():
            return f(*args, **kwargs)

    return wrapper


after_setup_logger.connect(setup_log)
after_setup_task_logger.connect(setup_log)

@queue.task
@needs_app_context
def refresh():
    for switch in models.Switch.query.all():
        _refresh_switch(switch)


def _refresh_switch(switch):
    with closing(_get_ssh_client(switch)) as client:
        _refresh_switch_ports(switch, client) # show interface bried + show running interface
        _refresh_vlans(switch, client) # show vlan
        _refresh_mac_address_table(switch, client) # show mac address-table
