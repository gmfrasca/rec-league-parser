import requests
import logging
import sys


class RsvpTool(object):

    DEFAULT_URL = 'https://teamlockerroom.com'

    def __init__(self, username, password, url=DEFAULT_URL,
                 finance=False, name_mapping={}, **kwargs):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.baseurl = url
        self.session = requests.session()
        self.username = username
        self.password = password
        self.finance = finance
        self.name_mapping = name_mapping
        self._logged_in = False
        self.login()

    def login(self):
        pass

    # TODO: Refactor to get_next_game_attendance_str
    def get_next_game_attendance(self):
        return 'NextGameAttendanceStr'

    def get_next_game_attendees(self):
        return 'NextGameAttendees'

    def reset_game_data(self):
        pass

    def try_checkin(self, name, status):
        raise NotImplementedError

    def get_next_game_lines(self):
        return None

    def get_team_fee_progress(self):
        return None

    def lookup_rsvp_user(self, in_name):
        '''
        Search through the name mapping to see if in_name is an alias
        default back to in_name if not found.
        '''
        for actual, aliases in self.name_mapping.items():
            if isinstance(aliases, str):
                if aliases == in_name:
                    return actual
            elif isinstance(aliases, list):
                for alias in aliases:
                    if alias == in_name:
                        return actual
        return in_name


def main():
    assert len(sys.argv) > 2
    tlr = RsvpTool(sys.argv[1], sys.argv[2])
    logging.debug(tlr.get_next_game_attendees())
    logging.debug(tlr.get_next_game_attendance())


if __name__ == '__main__':
    main()
