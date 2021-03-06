"""
Quick and Dirty table parser to read a team schedule
off of SportsEngine, a team stats-tracking website
"""
from bs4 import BeautifulSoup
from recleagueparser.schedules.schedule import Schedule
from recleagueparser.schedules.game import Game
import logging
import sys

SE_URL = 'http://www.pahl.org'
SE_SCHED_EXT = 'schedule/team_instance'


class SportsEngineSchedule(Schedule):

    # Expected Column Data Contents
    DEFAULT_COLUMNS = {
        'homelogo': None,
        'hometeam': None,
        'awaylogo': None,
        'awayteam': 2,
        'gameday': 0,
        'gametime': 4,
        'extras': None,
        'result': 1,
        'location': 3
    }
    CANCELLED_TEXT = "cancelled"

    def __init__(self, team_id, season_id, **kwargs):
        super(SportsEngineSchedule, self).__init__(
            team_id=team_id, season_id=season_id, **kwargs)
        self.team_name = self.parse_team_name()

    def parse_team_name(self):
        soup = BeautifulSoup(self.html_doc, 'html.parser')
        return soup.h2.a.text

    def get_schedule_url(self, team_id, season_id):
        # TODO subseason may not be necessary, appears to default with latest
        sched_params = '{0}?subseason={1}'.format(team_id, season_id)
        return '{0}/{1}/{2}'.format(SE_URL, SE_SCHED_EXT, sched_params)

    def retrieve_html_table(self, url):
        return self.retrieve_html_table_with_class(
            url, 'statTable sortable noSortImages')

    def parse_table(self):
        self._logger.info("Parsing Games from SportsEngine Data Table")
        games = []
        prevgame = None
        for game_row in self.html_table.find_all('tr'):
            cells = game_row.find_all('td')
            gamedate = cells[self.columns['gameday']].text
            gametime = self.get_game_time(cells[self.columns['gametime']])
            cancelled = self.is_game_cancelled(gametime)
            hometeam, awayteam = self.parse_teams(
                cells[self.columns['awayteam']])
            homescore, awayscore = self.parse_score(
                cells[self.columns['result']],
                cells[self.columns['awayteam']])
            final = self.is_score_final(cells[self.columns['result']])
            game = Game(gamedate, gametime, hometeam, homescore, awayteam,
                        awayscore, prevgame=prevgame, final=final,
                        cancelled=cancelled)
            games.append(game)
            prevgame = game
        self._logger.info("Parsed {} Games from Table".format(len(games)))
        return games

    def is_home_team(self, opponent):
        return True if opponent.div.text.strip()[:1] == '@' else False

    def is_score_final(self, score):
        # TODO: Should probably parse the "Status" column instead
        divs = score.find_all("div")
        return divs is not None and len(divs) > 1

    def is_game_cancelled(self, gametime):
        # TODO: Implement a better way to do this
        return gametime.strip().lower() == self.CANCELLED_TEXT

    def get_game_time(self, gametime_cell):
        gametime = gametime_cell.a if gametime_cell.a is not None else None
        if gametime is not None and gametime.span is not None:
            return gametime.text
        self._logger.debug("Could not find game time, assigning 12:01AM EST")
        return "12:01 AM EST"

    def parse_teams(self, opponent):
        opp_name = opponent.div.text if opponent.div.a is None else \
            opponent.div.a.text
        opp_name = opp_name.strip()
        if self.is_home_team(opponent):
            return self.team_name, opp_name
        return opp_name, self.team_name

    def parse_score(self, score, opponent):
        divs = score.find_all("div")
        if len(divs) < 1:
            return None, None
        score_link = divs[0].a if divs[0].a is not None else divs[1].a
        scoretext = score_link.text
        scores = [x.strip() for x in scoretext.split('-')]
        if self.is_home_team(opponent):
            return scores[0], scores[1]
        return scores[1], scores[0]


def main():
    assert len(sys.argv) > 2
    sched = SportsEngineSchedule(sys.argv[1], sys.argv[2])
    logging.basicConfig(level=logging.DEBUG)
    logging.debug(sched)


if __name__ == '__main__':
    main()
