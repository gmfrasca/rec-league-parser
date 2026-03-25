"""
Quick and Dirty table parser to read the player stats
off of DashPlatform/Daysmart Recreation, a team stats-tracking website
"""
from recleagueparser.player_stats.player_stats import PlayerStats
from recleagueparser.player_stats.player import Player
from bs4 import BeautifulSoup
import requests
import datetime


DASH_URL = "https://apps.daysmartrecreation.com"
DASH_STATS_EXT = '/dash/index.php?Action=Stats/index'
TEAM_STATS_EXT = '/dash/index.php?Action=Element/Stats/team_stats&hideForm=false'


class DashPlatformPlayerStats(PlayerStats):

    # Expected Column Data Contents
    COLUMNS = {
        'player_name': 0,
        'goals': 1,
        'assists': 2,
        'pim': 3,
        'goals_against': 4,
        'shots_against': 5,
        'saves': 6,
        'games_played': 7
    }

    def __init__(self, team_id, company_id, username, password,**kwargs):
        # Login required for PlayerStats in DashPlatform
        if username is None:
            raise ValueError("Username is required for DashPlatformPlayerStats")
        if password is None:
            raise ValueError("Password is required for DashPlatformPlayerStats")
        if company_id is None:
            raise ValueError("Company ID is required for DashPlatformPlayerStats")

        # Need to create the session *before* constructing the PlayerStats object
        self.team_id = team_id
        self.company_id = company_id
        self.session = self._login(username, password)
        super(DashPlatformPlayerStats, self).__init__(team_id=team_id, company_id=company_id, **kwargs)

    def _login(self, username, password):
        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=5)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        login_page=f"{DASH_URL}/dash/jsonapi/api/v1/customer/auth/token?company={self.company_id}"
        login_payload = {
            "grant_type": "client_credentials",
            "client_id": username,
            "client_secret": password,
            "stay_signed_in": True,
            "company": self.company_id,
            "company_code": self.company_id
        }
        r = session.post(login_page, data=login_payload)
        return session

    def send_get_request(self, url):
        self._logger.info(f"Retreiving Player Stats from Webpage: {url}")
        self.html_doc = self.session.get(url).text
        self.last_refresh = datetime.datetime.now()

    def get_stats_url(self, *args, **kwargs):
        return f"{DASH_URL}{TEAM_STATS_EXT}&teamID={self.team_id}&company={self.company_id}"

    def retrieve_html_tables(self, url):
        return self.retrieve_stats_table(url)

    def get_stat(self, row, data_name):
        if self.COLUMNS.get(data_name, -1) < 0:
            return ''
        return row[self.COLUMNS.get(data_name)].text.strip()

    def retrieve_stats_table(self, url):
        """
        Retrieve the raw html for the table on a Poinstreak Team
        stats webpage

        Args:
            url (str): The URL to parse a Poinstreak stats from

        Returns:
             a list of bs tbody elements containing the player stats
        """
        if self.is_stale:
            self._logger.info("Stats are stale, must be refreshed")
            self.send_get_request(url)
        soup = BeautifulSoup(self.html_doc, 'html.parser')
        div = soup.find("div", {'id': 'teamStats'})
        tables = div.find_all("table")
        return tables

    def parse_table(self):
        self._logger.info("Parsing Player Stat Table...")
        players = dict()
        player_table = self.html_tables[0]
        for player_row in player_table.find_all('tr'):
            if len(player_row.find_all('th')) > 0:
                # Skip header row
                continue
            cells = player_row.find_all('td')
            player_name = self.get_stat(cells, 'player_name')
            self._logger.debug("Adding player '{}'".format(player_name))
            player = Player(name=player_name,
                            games_played=self.get_stat(cells, 'games_played'),
                            goals=self.get_stat(cells, 'goals'),
                            assists=self.get_stat(cells, 'assists'),
                            penalties=self.get_stat(cells, 'penalties'),
                            penalties_in_minutes=self.get_stat(cells, 'pim'),
                            jersey_number=self.get_stat(cells,
                                                        'jersey_number'))
            players.update({player_name: player})
        player_dict = dict(players=players, goalies={})
        self._logger.debug("Player Dict: {}".format(player_dict))
        return player_dict
