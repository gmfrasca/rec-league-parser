from recleagueparser import parsetime as pt
import datetime

DEFAULT_COMPLETED_GAME_TIME = "12:01 AM EST"
LOCATION_JOINER = " - "

class Game(object):
    """Represents a game parsed from a Pointstreak schedule"""

    def __init__(self, date, time, hometeam, homescore, awayteam, awayscore,
                 year=None, prevgame=None, final=False, cancelled=False,
                 location=None, field=None):
        """ Store this game's relevant data """
        self.final = final
        self.cancelled = cancelled
        self.year = pt.determine_year(year)
        self.prevgame = prevgame
        self.parse_date(date, time, self.year, prevgame)
        self.hometeam = hometeam
        self.homescore = homescore
        self.awayteam = awayteam
        self.awayscore = awayscore
        self.location = location
        self.field = field

    @property
    def data(self):
        return dict(year=self.year,
                    date=self.date,
                    time=self.time,
                    full_gametime_str=self.full_gametime_str,
                    hometeam=self.hometeam,
                    homescore=self.homescore,
                    awayteam=self.awayteam,
                    awayscore=self.awayscore,
                    final=self.final,
                    cancelled=self.cancelled)

    @property
    def winning_team(self):
        if not self.homescore or not self.awayscore:
            return None
        if int(self.homescore) == int(self.awayscore):
            return 'tie'
        elif int(self.homescore) > int(self.awayscore):
            return self.hometeam
        return self.awayteam

    @property
    def future(self):
        return datetime.datetime.now() < self.full_gametime

    @property
    def full_gametime_str(self):
        descriptor = pt.FINAL_DESCRIPTOR if self.final else pt.FULL_DESCRIPTOR
        descriptor = pt.CANCELLED_DESCRIPTOR if self.cancelled else descriptor
        return self.full_gametime.strftime(descriptor)

    @property
    def full_location(self):
        joiner = LOCATION_JOINER if self.location else ""
        full_location = self.location if self.location else ""
        if self.field:
            full_location = f"{full_location}{joiner}{self.field}"
        return full_location

    def result_for_team(self, team_name):
        if self.winning_team is None:
            return None
        if self.winning_team == team_name:
            return 'win'
        if self.winning_team == 'tie':
            return 'tie'
        return 'loss'

    def parse_date(self, date, time, year, prevgame=None):
        # TODO: Determine if we should actually set includes_day
        if self.cancelled or self.final:
            time = DEFAULT_COMPLETED_GAME_TIME

        self.date = pt.normalize_date(date.strip(), includes_day=True)
        self.time = pt.normalize_time(time.strip())
        self.full_gametime = pt.assemble_full_datetime(date, time, year)

        if prevgame is not None:
            if prevgame.full_gametime > self.full_gametime:
                next_year = str(int(self.year) + 1)
                self.parse_date(date, time, next_year, prevgame)

    def __repr__(self):
        """Print this game's most relevant info all together"""
        if self.homescore and self.awayscore:
            return '{0} [{1}] : [{2}] {3} on {4}'.format(
                self.hometeam, self.homescore, self.awayscore,
                self.awayteam, self.full_gametime_str)

        future_game_tagline = '{0} vs {1} at {2}'.format(self.hometeam,
                                                         self.awayteam,
                                                         self.full_gametime_str)
        if self.full_location:
            future_game_tagline = f"{future_game_tagline}, {self.full_location}"
        return future_game_tagline
