from recleagueparser.rsvp_tools import exceptions as rsvptoolexceptions
from recleagueparser.rsvp_tools.rsvp_tool import RsvpTool
from bs4 import BeautifulSoup
from re import sub
from decimal import Decimal
from functools import reduce
from requests import Request
import logging
import sys
import re


DEFAULT_URL = 'https://new.benchapp.com'
LOGIN_URL = '/player-area/ajax/login.php'
LOGOUT_URL = '/logout'
NEXT_GAME_URL = '/schedule/next-event'
CHECKIN_URL = '/schedule-area/ajax/setAttendance.php'
FINANCES_URL = '/team/finances/fees/index.html'

PROGRESS_BAR_CHARS = 20


class BenchApp(RsvpTool):

    def __init__(self, username, password, **kwargs):
        super(BenchApp, self).__init__(username, password, DEFAULT_URL,
                                       **kwargs)
        self.next_game_data = None
        self.retrieve_next_game_page()
        self.retrieve_finances_page()

    def login(self):
        if self._logged_in:
            self._logger.info("Already logged into BenchApp")
            return
        try:
            self._logger.info("Logging into BenchApp")
            data = {"email": self.username, "password": self.password}
            req = Request(
                "POST",
                f"{self.baseurl}{LOGIN_URL}",
                files={
                    "email": (None, data["email"]),
                    "password": (None, data["password"]),
                }
            ).prepare()
            resp = self.session.send(req)
            self._logger.debug(resp.text)
            self._logged_in = True
        except Exception:
            return
            self._logger.warning("Could not log into BenchApp")

    def logout(self):
        self.session.post("{0}{1}".FORMAT(self.baseurl, LOGOUT_URL))

    def parse_playeritem(self, playeritem):
        text = playeritem.findAll("a", {"href": "#profile"})[0]
        date = text.small
        name = date.previous_sibling
        return name, date

    @property
    def has_upcoming_game(self):
        page = self.get_next_game_page().text
        soup = BeautifulSoup(page, 'html.parser')
        no_results_div = soup.find_all("div", {"class": "noResults"})
        return len(no_results_div) == 0

    def get_next_game_page(self):
        return self.next_game

    def retrieve_next_game_page(self):
        self.login()
        self._logger.info("Retrieving Next Game Page from BenchApp")
        self.next_game = self.session.get('{0}{1}'.format(self.baseurl,
                                                          NEXT_GAME_URL))

    def retrieve_finances_page(self):
        if self.finance:
            self.login()
            self._logger.info("Retrieving Finances Page from BenchApp")
            self.finance_page = self.session.get('{0}{1}'.format(self.baseurl,
                                                                 FINANCES_URL))

    def get_finances_page(self):
        return self.finance_page

    def reset_game_data(self):
        self.next_game_data = None
        self.retrieve_next_game_page()

    def get_next_game_data(self):
        self._logger.info("Parsing Attendance data from BenchApp")
        if self.next_game_data is not None:
            return self.next_game_data
        if self.has_upcoming_game is False:
            return dict()
        page = self.get_next_game_page().text
        soup = BeautifulSoup(page, 'html.parser')
        # These don't work anymore
        # in_count = soup.find("div", {"class": "inCount"}).text
        # out_count = soup.find("div", {"class": "outCount"}).text
        # data = dict(in_count=in_count, out_count=out_count)
        data = dict()
        for checkin_type in ['attending', 'notAttending',
                             'waitlist', 'unknown']:
            players = soup.find("ul", {"id": checkin_type})
            playeritems = players.findAll("li", {"class": "playerItem"})
            player_list = list()
            for playeritem in playeritems:
                player, date = self.parse_playeritem(playeritem)
                player_list.append(dict(player=player, date=date))
            data.update({checkin_type: player_list})
        self.next_game_data = data
        return data

    def moneytext_to_float(self, moneytext):
        return float(Decimal(sub(r'[^\d.-]', '', moneytext)))

    def get_team_fee_stats(self):
        if self.finance:
            self._logger.info("Parsing TeamFee Stats from BenchApp")
            page = self.get_finances_page().text
            soup = BeautifulSoup(page, 'html.parser')
            rosterlist = soup.find("table", {"id": "rosterList"})
            footer = rosterlist.find("tfoot")
            items = footer.find_all("td")

            paid = self.moneytext_to_float(items[2].text)
            fee = self.moneytext_to_float(items[1].text)

            # Do calculations here
            percent = 1.0
            try:
                percent = paid / fee
            except ZeroDivisionError:
                pass
            return fee, paid, percent
        return 0, 0, 1.0

    def get_team_fee_progress(self):
        fee, paid, percent = self.get_team_fee_stats()
        num_x = int(PROGRESS_BAR_CHARS * percent)
        num_rem = PROGRESS_BAR_CHARS - num_x
        x_string = '#' * num_x
        rem_string = '-' * num_rem
        return "[{}{}] {:.2f}%\r\n (${:.2f} / ${:.2f})".format(
            x_string, rem_string, 100 * percent, paid, fee)

    def get_list_of_player_names(self, list_type):
        data = self.get_next_game_data()
        player_list = data.get(list_type, list())
        names = list()
        for player in player_list:
            names.append(player.get('player', None).strip())
        return names

    def get_list_of_attending_players(self):
        return self.get_list_of_player_names('attending')

    def get_list_of_not_attending_players(self):
        return self.get_list_of_player_names('notAttending')

    def get_list_of_waitlisted_players(self):
        return self.get_list_of_player_names('waitlist')

    def get_list_of_unknown_status_players(self):
        return self.get_list_of_player_names('unknown')

    def get_number_checked_in(self):

        return len(self.get_list_of_attending_players())

    def get_number_checked_out(self):
        return len(self.get_list_of_not_attending_players())

    def get_number_waitlisted(self):
        return len(self.get_list_of_waitlisted_players())

    def get_number_of_unknown_status_players(self):
        return len(self.get_list_of_unknown_status_players())

    def get_next_game_attendance(self):
        self._logger.info("Getting next game's attendance")
        if self.has_upcoming_game:
            return "In: {0}, Out: {1}, Waitlist: {2}, No Status: {3}".format(
                self.get_number_checked_in(),
                self.get_number_checked_out(),
                self.get_number_waitlisted(),
                self.get_number_of_unknown_status_players())
        else:
            return "No upcoming games found."

    def get_next_game_attendees(self):
        self._logger.info("Getting next game's attendees")
        if self.has_upcoming_game:
            in_list = self.get_list_of_attending_players()
            out_list = self.get_list_of_not_attending_players()
            wait_list = self.get_list_of_waitlisted_players()
            unkn_list = self.get_list_of_unknown_status_players()
            in_str = reduce((lambda x, y: '{0}, {1}'.format(x, y)), in_list) \
                if len(in_list) > 0 else "None"
            out_str = reduce((lambda x, y: '{0}, {1}'.format(x, y)),
                             out_list) if len(out_list) > 0 else "None"
            wait_str = reduce((lambda x, y: '{0}, {1}'.format(x, y)),
                              wait_list) if len(wait_list) > 0 else "None"
            unkn_str = reduce((lambda x, y: '{0}, {1}'.format(x, y)),
                              unkn_list) if len(unkn_list) > 0 else "None"
            return ("In: {0}\r\nOut: {1}\r\nWaitlist: {2}" +
                    "\r\nNo Status: {3}").format(in_str, out_str,
                                                 wait_str, unkn_str)
        else:
            return "No upcoming games found."

    def get_next_game_lines(self):
        self._logger.debug("Getting next game's positions")
        self.login()
        if self.has_upcoming_game is False:
            return "No upcoming games found."
        page = self.get_next_game_page().text
        soup = BeautifulSoup(page, 'html.parser')
        controls = soup.find('div', {'class': 'mainControls'}).find_all('a')
        line_url = None
        for control in controls:
            line_url = control.get('href') if \
                control.get('href').startswith('/schedule/lines') else line_url
        response = self.session.get('{0}{1}'.format(self.baseurl, line_url))
        soup = BeautifulSoup(response.text, 'html.parser')
        lines = {
            'forwards': [
                {
                    'leftwing': self.get_player_in_line_pos(soup, 'fl1-lw'),
                    'center': self.get_player_in_line_pos(soup, 'fl1-c'),
                    'rightwing': self.get_player_in_line_pos(soup, 'fl1-rw')
                },
                {
                    'leftwing': self.get_player_in_line_pos(soup, 'fl2-lw'),
                    'center': self.get_player_in_line_pos(soup, 'fl2-c'),
                    'rightwing': self.get_player_in_line_pos(soup, 'fl2-rw')
                },
                {
                    'leftwing': self.get_player_in_line_pos(soup, 'fl3-lw'),
                    'center': self.get_player_in_line_pos(soup, 'fl3-c'),
                    'rightwing': self.get_player_in_line_pos(soup, 'fl3-rw')
                },
                {
                    'leftwing': self.get_player_in_line_pos(soup, 'fl4-lw'),
                    'center': self.get_player_in_line_pos(soup, 'fl4-c'),
                    'rightwing': self.get_player_in_line_pos(soup, 'fl4-rw')
                },
            ],
            'defense': [
                {
                    'left': self.get_player_in_line_pos(soup, 'dl1-ld'),
                    'right': self.get_player_in_line_pos(soup, 'dl1-rd')
                },
                {
                    'left': self.get_player_in_line_pos(soup, 'dl2-ld'),
                    'right': self.get_player_in_line_pos(soup, 'dl2-rd')
                },
                {
                    'left': self.get_player_in_line_pos(soup, 'dl3-ld'),
                    'right': self.get_player_in_line_pos(soup, 'dl3-rd')
                }
            ],
            'goalies': [
                self.get_player_in_line_pos(soup, 'gl-1'),
                self.get_player_in_line_pos(soup, 'gl-2'),
            ]

        }
        return self.construct_line_str(lines)

    def construct_line_str(self, lines):
        self._logger.debug("Formatting Lines Text")
        line_str = '---FORWARDS---'
        for line in lines.get('forwards'):
            lw = line.get('leftwing', None)
            rw = line.get('rightwing', None)
            center = line.get('center', None)
            lw = '' if lw is None else lw
            rw = '' if rw is None else rw
            center = '' if center is None else center
            if all(v is None for v in line.values()) is False:
                line_str = '{0}\r\n{1} - {2} - {3}'.format(line_str, lw,
                                                           center, rw)
        line_str = '{0}\r\n---DEFENSE---'.format(line_str)
        for line in lines.get('defense'):
            ld = line.get('left', None)
            rd = line.get('right', None)
            ld = '' if ld is None else ld
            rd = '' if rd is None else rd
            if all(v is None for v in line.values()) is False:
                line_str = '{0}\r\n{1} - {2}'.format(line_str, ld, rd)
        line_str = '{0}\r\n---GOALIES---'.format(line_str)
        for goalie in lines.get('goalies'):
            if goalie is not None:
                line_str = '{0}\r\n{1}'.format(line_str, goalie)
        self._logger.debug("Lines:\n{}".format(line_str))
        return line_str

    def get_player_in_line_pos(self, soup, pos):
        pos_item = soup.find('div', {'data-position': pos})
        if pos_item is None:
            return None
        player_item = pos_item.find('span', {'class': 'playerName'})
        player_num = player_item.span
        player_name = player_num.previous_sibling
        return player_name.strip()

    def try_checkin(self, name, status='in'):
        self.login()
        name = self.lookup_rsvp_user(name)
        self._logger.info("RSVPing {} with status '{}'".format(name, status))
        if self.has_upcoming_game is False:
            return
        page = self.get_next_game_page().text
        soup = BeautifulSoup(page, 'html.parser')
        players = soup.find_all('li',
                                id=lambda x: x and x.startswith('player-'))
        found = False
        playeritem = None
        self._logger.info("Looking up player {}".format(name))
        for player in players:
            # Checkin By ID, exact match
            if player.get('id').endswith(name) or \
                    re.search(name.lower(), player.text.lower()) is not None:
                # Multiple results, too ambigous so can't continue
                if found:
                    raise rsvptoolexceptions.MultiplePlayersCheckinException(
                        "Multiple Players with same name found")
                else:
                    found = True
                    playeritem = player
        self._logger.info("Done searching")
        if found:
            self._logger.info(
                "Found {}, attempting to RSVP with '{}'".format(name, status))
            try:
                checkin = playeritem.find("a", {"href": "#IN"})
                checkin = playeritem.find(
                    "div", {'class', 'contextualWrapper'})
                checkin_fn = checkin.get('onclick', '')
                params = checkin_fn.split(';')[0].split(')')[0].split('(')[1]
                (teamID, seasonID, gameID, gameKey, playerID,
                 ignore, refresh) = params.split(',')
                data = dict(teamID=int(teamID),
                            gameID=int(gameID),
                            seasonID=int(seasonID),
                            playerID=int(playerID),
                            status=str(status),
                            gameKey=gameKey.strip("'"))
                self.session.get('{0}{1}'.format(DEFAULT_URL, CHECKIN_URL),
                                 params=data)
                self._logger.info("Success.")
            except Exception:
                raise rsvptoolexceptions.CheckinFailedException(
                    "ERROR::Could not check in {0}".format(name))
        else:
            raise rsvptoolexceptions.NoPlayerFoundCheckinException(
                "ERROR::Could not find player {0}".format(name))

    def get_duty_assignment(self, duty_type="Drinks"):
        self._logger.debug("Getting next game's data")
        self.login()
        if self.has_upcoming_game is False:
            return "No upcoming games found."
        page = self.get_next_game_page().text
        soup = BeautifulSoup(page, 'html.parser')
        duties = soup.find_all('div', {'class': 'duty tooltip'})
        for duty in duties:
            dtype = duty.find('div', {'class': 'type'}).text
            dname = duty.find('div', {'class': 'name'}).text
            if duty_type.lower() == dtype.lower():
                return dname
        return ""

    def get_all_duty_assignments(self):
        self._logger.debug("Getting next game's data")
        self.login()
        if self.has_upcoming_game is False:
            return "No upcoming games found."
        page = self.get_next_game_page().text
        soup = BeautifulSoup(page, 'html.parser')
        duties_str = "Assigned Duties:"
        duty_divs = soup.find_all('div', {'class': 'duty tooltip'})
        if len(duty_divs) > 0:
            for d in duty_divs:
                duties_str = f"{duties_str}\r\n{d['title']}"
        else:
            duties_str = f"{duties_str}\r\nNo assignments"
        return duties_str


def main():
    assert len(sys.argv) > 2
    logging.basicConfig(level=logging.DEBUG)
    ba = BenchApp(sys.argv[1], sys.argv[2])
    logging.debug(ba.get_next_game_attendees())
    logging.debug(ba.get_next_game_attendance())
    logging.debug(ba.get_next_game_lines())


if __name__ == '__main__':
    main()
