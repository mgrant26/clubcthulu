""" Utility Classes
"""
from datetime import datetime, timedelta

class Timer():
    """ Delta Timer class
    """
    def __init__(self):
        self.last_loop = datetime.now()

    def get_delta(self) -> timedelta:
        """ Returns the delta
        """
        time = datetime.now()
        delta = time - self.last_loop
        self.last_loop = time
        return delta
