class CheckinException(Exception):
    pass


class MultiplePlayersCheckinException(CheckinException):
    pass


class NoPlayerFoundCheckinException(CheckinException):
    pass


class CheckinFailedException(CheckinException):
    pass
