"""
Quick and Dirty table parser to read a team schedule
off of DashPlatform, a team stats-tracking website
"""
import recleagueparser.parsetime as pt
from bs4 import BeautifulSoup
from recleagueparser.schedules.schedule import Schedule
from recleagueparser.schedules.game import Game
import datetime
import requests
import logging
import sys


class DashPlatformSchedule(Schedule):

    DASH_URL = 'https://apps.dashplatform.com/'
    SCHEDULE_URL = '/dash/index.php?Action=Team/index'
    GAMESTATS_URL = '/dash/index.php?Action=Stats/game'
    LOGIN_PAGE = '/dash/jsonapi/api/v1/customer/auth/token'

    DEFAULT_COLUMNS = {
        'homescore': 2,
        'hometeam': 3,
        'awayscore': 4,
        'awayteam': 5,
    }

    def __init__(self, team_id, company_id, columns=None, default_game_final=False,
    username=None, password=None, **kwargs):
        super(DashPlatformSchedule, self).__init__(team_id=team_id,
                                                   company_id=company_id,
                                                   email=None,
                                                   password=None,
                                                   columns=columns, **kwargs)
        self.html_doc = None
        self.team_id = team_id
        self.company_id = company_id
        self.default_game_final = default_game_final
        self.url = self.get_schedule_url(self.team_id, self.company_id)
        self.authenticated_session = None
        if username is not None and password is not None:
            self.authenticated_session = self._login(username, password)
        self.refresh_schedule()

    def _login(self, username, password):
        if self.authenticated_session is None:
            session = requests.Session()
            login_page=f"https://apps.daysmartrecreation.com/dash/jsonapi/api/v1/customer/auth/token?company={self.company_id}"
            login_payload = {
                "grant_type": "client_credentials",
                "client_id": username,
                "client_secret": password,
                "stay_signed_in": True,
                "company": self.company_id,
                "company_code": self.company_id
            }

            session.post(login_page, data=login_payload)
            self.authenticated_session = session
        return self.authenticated_session

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
                id = self.find_game_id(game_row)
                game = Game(gamedate, gametime, hteam, hscore,
                            ateam, ascore, prevgame=prevgame, final=final,
                            location=location, field=field, id=id)
                games.append(game)
                prevgame = game
        self._logger.info("Parsed {} Games from Data Table".format(len(games)))
        return games

    def stats_available(self, game):
        return game.id is not None

    def find_game_id(self, game_row):
        id_link = game_row.find('a', {'title': 'Stats'})
        id = None
        if id_link:
            id_ext = id_link.get('href').split("/")[-1]
            id_params = id_ext.split("&")
            event_ids = [x for x in id_params if "eventID" in x]
            if len(event_ids) > 0:
                id = event_ids[0].split("=")[-1]
        return id

    def get_game_stats_url(self, game_id):
        return "{0}{1}&company={2}&eventID={3}".format(self.DASH_URL, self.GAMESTATS_URL, self.company_id, game_id)

    def get_game_stats(self, game_id):
        game_stats_cols = {
            'player_name': 0,
            'goals': 1,
            'assists': 2,
            'pim': 3,
            'goals_against': 4,
            'shots_against': 5,
            'saves': 6,
            'games_played': 7
        }
        if not self.authenticated_session:
            return {}
        self._logger.info(f"Getting game stats for game ID: {game_id}")
        url = self.get_game_stats_url(game_id)
        page = self.authenticated_session.get(url)
        stats_soup = BeautifulSoup(page.text, 'html.parser')
        player_stats_table = stats_soup.find_all("table")[3]
        inner_tables = player_stats_table.find_all("table", {'class': 'tablecondensed'})
        stats = {}
        for inner_table in inner_tables:
            team_name = inner_table.find("th").text.split("-")[0].strip()
            stats[team_name] = {}
            first = True
            for row in inner_table.find_all("tr"):
                if first:
                    first = False
                    continue
                cells = row.find_all("td")
                if len(cells) > 0:
                    player_name = cells[game_stats_cols['player_name']].a.text.strip()
                    stats[team_name][player_name] = {
                        'goals': int(cells[game_stats_cols['goals']].text.strip()),
                        'assists': int(cells[game_stats_cols['assists']].text.strip()),
                        'pim': int(cells[game_stats_cols['pim']].text.strip()),
                        'goals_against': int(cells[game_stats_cols['goals_against']].text.strip()),
                        'shots_against': int(cells[game_stats_cols['shots_against']].text.strip()),
                        'saves': int(cells[game_stats_cols['saves']].text.strip()),
                        'games_played': int(cells[game_stats_cols['games_played']].text.strip()),
                    }
        return stats

    def get_stats_summary(self, game_id):
        game_stats = self.get_game_stats(game_id)
        summary = "Game Summary:"
        goals_by = ""
        assists_by = ""
        pim_by = ""

        # Get goals by player
        for team, players in game_stats.items():
            for player, stats in players.items():
                if stats['goals'] > 0:
                    goals_by += f"[{team}] {player} ({stats['goals']})\n"
                if stats['assists'] > 0:
                    assists_by += f"[{team}] {player} ({stats['assists']})\n"
                if stats['pim'] > 0:
                    pim_by += f"[{team}] {player} ({stats['pim']})\n"
        if goals_by:
            summary += f"\nGoals by:\n{goals_by}"
        if assists_by:
            summary += f"\nAssists by:\n{assists_by}"
        if pim_by:
            summary += f"\nPenalties:\n{pim_by}"
        return summary

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
    logging.basicConfig(level=logging.INFO)
    sched = DashPlatformSchedule(team_id=sys.argv[1], company_id=sys.argv[2])
    logging.info(sched)
