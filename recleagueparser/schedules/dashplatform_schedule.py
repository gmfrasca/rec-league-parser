"""
Quick and Dirty table parser to read a team schedule
off of DashPlatform, a team stats-tracking website
"""
import recleagueparser.parsetime as pt
from bs4 import BeautifulSoup
from recleagueparser.schedules.schedule import Schedule
from recleagueparser.schedules.game import Game
import datetime
import logging
import sys


class DashPlatformSchedule(Schedule):

    DASH_URL = 'https://apps.dashplatform.com/'
    SCHEDULE_URL = '/dash/index.php?Action=Team/index'

    DEFAULT_COLUMNS = {
        'homescore': 2,
        'hometeam': 3,
        'awayscore': 4,
        'awayteam': 5,
    }

    def __init__(self, team_id, company_id, columns=None, default_game_final=False, **kwargs):
        super(DashPlatformSchedule, self).__init__(team_id=team_id,
                                                   company_id=company_id,
                                                   columns=columns, **kwargs)
        self.html_doc = None
        self.team_id = team_id
        self.company_id = company_id
        self.default_game_final = default_game_final
        self.url = self.get_schedule_url(self.team_id, self.company_id)
        self.refresh_schedule()

    def get_schedule_url(self, team_id, company):
        sched_params = 'teamid={0}&company={1}'.format(team_id, company)
        return "{0}{1}&{2}".format(self.DASH_URL, self.SCHEDULE_URL,
                                   sched_params)

    def retrieve_html_table(self, url):
        table_class = 'list-group'
        if self.schedule_is_stale:
            self._logger.info("Schedule is stale, refreshing")
            self.send_get_request(url)
        soup = BeautifulSoup(self.html_doc, 'html.parser')
        self.team_name = self.retrieve_team_name(soup)
        return soup.find("div", {'class': table_class})

    def retrieve_team_name(self, soup):
        header = soup.find("h2")
        if header:
            return header.text.split(" ", maxsplit=1)[1]
        return None

    def parse_table(self):
        """
        Get a list PoinstreakGames by parsing the raw html retrieved
        from the Poinstreak Team Schedule webpage

        Returns:
            a list of PoinstreakGames in order from first to last
        """
        self._logger.info("Parsing games from DashPlatform Data Table")
        games = []
        now = datetime.datetime.now()
        if self.html_table:
            prevgame = None
            game_rows = self.html_table.find_all('div',
                                                 {'class': 'list-group-item'})
            for game_row in game_rows:
                # Parse Date
                gamedate_cell = game_row.find(
                    'div', {'class': 'event__date'}).div.find_all('div')
                cell_date = gamedate_cell[0].text
                cell_time = gamedate_cell[1].text.split(' ', 1)[1]
                structured = '{} {}'.format(cell_date, cell_time)
                parsed_date = pt.normalize_date(structured, now.year,
                                           return_type=datetime.datetime)
                gamedate = parsed_date.strftime(pt.DATE_DESCRIPTOR)

                parsed_time = pt.normalize_time(
                    structured, return_type=datetime.datetime
                )
                gametime = parsed_time.strftime(pt.TIME_DESCRIPTOR)

                # Parse Score
                event_cells = game_row.find('div', {'class': 'event__details'})
                score_cells = event_cells.find_all('div', recursive=False)
                away_cells = score_cells[0].find_all('div')
                home_cells = score_cells[1].find_all('div')

                # Default Team/Score values
                ateam = "AWAY"
                hteam = "HOME"
                ascore = None
                hscore = None

                # Track if Game has started
                game_started = False

                # Set Away Team and Score
                try:
                    ateam = away_cells[0].a.text
                    ascore = away_cells[1].text
                    if ascore == "-":
                        ascore = None
                    else:
                        game_started = True

                except (AttributeError, IndexError) as err:
                    self._logger.debug("Could not parse away cell team or score, using defaults")

                # Set Home Team and Score
                try:
                    hteam = home_cells[0].a.text
                    hscore = home_cells[1].text
                    if hscore == "-":
                        hscore = None
                    else:
                        game_started = True
                except (AttributeError, IndexError) as err:
                    self._logger.debug("Could not parse home cell team or score, using defaults")

                # Game Location
                location = None
                field = None
                try:
                    location_cells = score_cells[2].find_all('div')
                    field_cells = score_cells[3].find_all('div')
                    location = location_cells[0].small.text
                    field = field_cells[0].small.text
                except:
                    self._logger.debug("Could not find game Location, skipping.")
                    
                final = self.is_score_final(None, game_started)
                game = Game(gamedate, gametime, hteam, hscore,
                            ateam, ascore, prevgame=prevgame, final=final,
                            location=location, field=field)
                games.append(game)
                prevgame = game
        self._logger.info("Parsed {} Games from Data Table".format(len(games)))
        return games

    def is_score_final(self, score, game_started=False):
        if game_started:
            return self.default_game_final  # TODO: Implement
        return False

    def parse_game(self, game_cell):
        if game_cell.div:
            gamedate = game_cell.div
            gametime = gamedate.next_sibling
            return gamedate.text, gametime
        return 'Mon Jan 1st', '12:34pm'

    def parse_score(self, score_cell):
        if score_cell.b:
            score = score_cell.b.text.split()
            return score[0], score[2]
        return None, None

    def parse_teams(self, teams_cell):
        links = teams_cell.find_all('a')
        return links[0].text, links[1].text


if __name__ == '__main__':
    assert len(sys.argv) > 2
    logging.basicConfig(level=logging.DEBUG)
    sched = DashPlatformSchedule(team_id=sys.argv[1], company_id=sys.argv[2])
    logging.debug(sched)
