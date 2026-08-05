class Team(object):
    """Represents a team parsed from a schedule"""

    def __init__(self, name, id=None):
        self.name = name
        self.id = id if id else name
