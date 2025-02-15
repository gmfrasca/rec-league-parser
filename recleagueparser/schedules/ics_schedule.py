"""
Quick and Dirty ics parser to read a team schedule
"""
from recleagueparser.schedules.schedule import Schedule
from recleagueparser.schedules.game import Game
import recleagueparser.parsetime as pt
from icalendar import Calendar
import sys

class ICSSchedule(Schedule):

    def __init__(self, url=None, file=None, opponent_delimiter="vs.", **kwargs):
        self.url = url
        self.file = file
        self.opponent_delimiter = opponent_delimiter
        super(ICSSchedule, self).__init__(url, **kwargs)
        self.html_doc = None
        self.refresh_schedule()

    def get_schedule_url(self, *args, **kwargs):
        return self.url

    def retrieve_html_table(self, url):
        if self.schedule_is_stale:
            self._logger.info("Schedule is stale, refreshing")
            if self.url:
                self.send_get_request(url)
            else:
                with open(self.file, 'r') as f:
                    self.html_doc = f.read()
        return self.html_doc

    def parse_table(self):
        """
        Get a list Games by parsing the ics file

        Returns:
            a list of Games in order from first to last
        """
        self._logger.info("Parsing games from ICS file")
        games = []
        prevgame = None
        if self.html_doc:
            cal = Calendar.from_ical(self.html_doc)
            for i in cal.walk():
                if i.name == "VEVENT":
                    # Parse Teams
                    hteam, ateam = self.parse_summary(i.get("summary"))

                    # Parse Date
                    dt = i.get("dtstart").dt
                    gamedate = dt.strftime(pt.DATE_DESCRIPTOR)
                    gameyear = dt.year
                    gametime = dt.strftime(pt.TIME_DESCRIPTOR)

                    # Parse Score  #TODO: implement
                    hscore = 0
                    ascore = 0
                    final = False

                    # Add game to Schedule
                    game = Game(gamedate, gametime, hteam, hscore,
                                ateam, ascore, year=gameyear,
                                prevgame=prevgame, final=final)
                    games.append(game)
                    prevgame = game
        self._logger.info("Parsed {} Games from Data Table".format(len(games)))  
        return games


    def parse_summary(self, summary):
        delim_len = len(self.opponent_delimiter)
        delim_index = summary.find(self.opponent_delimiter)
        if delim_index < 0:
            return "", ""
        return summary[0:delim_index].strip(), summary[delim_index+delim_len:].strip()


if __name__ == '__main__':
    assert len(sys.argv) > 1
    param = sys.argv[1]
    if param.startswith("http"):
        sched = ICSSchedule(url=sys.argv[1])
    else:
        sched = ICSSchedule(file=sys.argv[1])
    print(sched)
