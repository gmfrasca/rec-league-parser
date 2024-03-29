"""
Quick and Dirty table parser to read the player stats
off of SportsEngine, a team stats-tracking website
"""
from recleagueparser.player_stats.player_stats import PlayerStats
from recleagueparser.player_stats.player import Player


SE_URL = 'http://www.pahl.org'
SE_STATS_EXT = 'stats/team_instance'


class SportsEnginePlayerStats(PlayerStats):

    # TODO: spec/override in config
    # Expected Column Data Contents
    COLUMNS = {
        'jersey_number': 0,
        'player_name': 1,
        'games_played': 2,
        'goals': 3,
        'assists': 4,
        'points': 5,
        'penalties': 6,
        'pim': 7,
        'wins': 3,
        'losses': 4,
        'ties': -1,
        'goals_against': 5
    }

    def get_stats_url(self, team_id, season_id):
        tab = 'tab=team_instance_player_stats'
        sched_params = '{0}?subseason={1}&{2}'.format(team_id, season_id, tab)
        return '{0}/{1}/{2}'.format(SE_URL, SE_STATS_EXT, sched_params)

    def retrieve_html_tables(self, url):
        return self.retrieve_html_tables_with_class(
            url, 'dataTable statTable theme-stat-table')

    def get_stat(self, row, data_name):
        if self.COLUMNS.get(data_name, -1) < 0:
            return ''
        return row[self.COLUMNS.get(data_name)].text.strip()

    # TODO
    def parse_table(self):
        self._logger.info("Parsing Player Stat Table...")
        players = dict()
        goalies = dict()
        player_table = self.html_tables[0]
        goalie_table = self.html_tables[1]

        self._logger.info("Parsing Players Stats...")
        for player_row in player_table.find_all('tr'):
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

        self._logger.info("Parsing Goalie Stats...")
        for goalie_row in goalie_table.find_all('tr'):
            cells = goalie_row.find_all('td')
            goalie_name = self.get_stat(cells, 'player_name')
            self._logger.debug("Adding goalie '{}'".format(goalie_name))
            goalie = Player(name=goalie_name,
                            games_played=self.get_stat(cells, 'games_played'),
                            wins=self.get_stat(cells, 'wins'),
                            losses=self.get_stat(cells, 'losses'),
                            ties=self.get_stat(cells, 'ties'),
                            goals_against=self.get_stat(cells,
                                                        'goals_against'))
            goalies.update({goalie_name: goalie})
        player_dict = dict(players=players, goalies=goalies)
        self._logger.debug("Player Dict: {}".format(player_dict))
        return player_dict
