from recleagueparser.player_stats.sportsengine_player_stats \
    import SportsEnginePlayerStats
from recleagueparser.player_stats.dashplatform_player_stats \
    import DashPlatformPlayerStats


class PlayerStatsFactory(object):

    def create(stats_type, **kwargs):
        if stats_type == 'sportsengine':
            return SportsEnginePlayerStats(**kwargs)
        elif stats_type == 'dash' or stats_type == 'daysmart':
            return DashPlatformPlayerStats(**kwargs)
        else:
            raise ValueError("Stats Tool Type '{0}' not found"
                             .format(stats_type))

    create = staticmethod(create)
