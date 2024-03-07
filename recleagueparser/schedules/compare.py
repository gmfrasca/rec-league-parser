from recleagueparser.schedules.schedule_factory import ScheduleFactory
import difflib
import logging
import sys

class ScheduleComparer(object):

    DIFF_PREFIXES = ["- ", "? ", "+ "]

    def __init__(self, schedule1, schedule2):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.schedule1 = schedule1
        self.schedule2 = schedule2
        self.differ = difflib.Differ()

    def sched_diff(self, only_future_games=True, long_diff=False):
        self.schedule1.refresh_schedule()
        self.schedule2.refresh_schedule()
        s1 = self.schedule1.future_games if only_future_games else self.schedule1
        s2 = self.schedule2.future_games if only_future_games else self.schedule2
        s1 = str(s1).splitlines(keepends=True)
        s2 = str(s2).splitlines(keepends=True)
        res = list(self.differ.compare(s1, s2))
        if not long_diff:
            res = [x for x in res if x[0:2] in self.DIFF_PREFIXES]
        return ''.join(res)


if __name__ == '__main__':
    assert len(sys.argv) > 2
    param1 = sys.argv[1]
    param2 = sys.argv[2]
    if param1.startswith("http"):
        sched1 = ScheduleFactory.create("ics", url=param1)
    else:
        sched1 = ScheduleFactory.create("ics", file=param1)

    if param2.startswith("http"):
        sched2 = ScheduleFactory.create("ics", url=param2)
    else:
        sched2 = ScheduleFactory.create("ics", file=param2)

    sc = ScheduleComparer(sched1, sched2)
    print(sc.sched_diff())
