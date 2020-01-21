from recleagueparser.rsvp_tools.rsvp_tool import RsvpTool
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
from google.oauth2 import service_account
import logging
import re
import io


ENTRY_REGEX = r'^[\*-]\s+.*$'
REMOVE_REGEX = r'^[\*-]\s+'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveSignupSheet(RsvpTool):

    def __init__(self, cred_file, file_id, skip_lists=0, **kwargs):
        self._logger = logging.getLogger(self.__class__.__name__)
        self.cred_file = cred_file
        self.skip_lists = skip_lists
        self.file_id = file_id

    @property
    def credentials(self):
        return service_account.Credentials.from_service_account_file(
            self.cred_file, scopes=SCOPES)

    def login(self):
        self.schedule = self.parse_file()

    def retrieve_text(self):
        service = build('drive', 'v3', credentials=self.credentials)
        request = service.files().export_media(fileId=self.file_id,
                                               mimeType='text/plain')
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue().decode('utf-8')

    def parse_file(self):
        text = self.retrieve_text()
        lists = []
        prev_line = ''
        in_list = False
        title = ''
        players = []

        for line in text.splitlines():
            current = line.strip()
            if re.match(ENTRY_REGEX, current):
                if not in_list:
                    in_list = True
                    title = prev_line
                players.append(re.sub(REMOVE_REGEX, '', current))
            elif in_list:
                in_list = False
                lists.append({'title': title, 'players': players.copy()})
                players = []
            prev_line = current
        if in_list:
            lists.append({'title': title, 'players': players.copy()})
        return lists

    def get_game(self, game_id):
        self.login()
        game_id = game_id + self.skip_lists
        return {} if game_id >= len(self.schedule) else self.schedule[game_id]

    def get_outage_list(self):
        self.login()
        if self.skip_lists == 0 or len(self.schedule) == 0:
            return {}
        return self.schedule[0]

    def get_next_game(self):
        return self.get_game(0)

    # TODO: Refactor to get_next_game_attendance_str
    def get_next_game_attendance(self):
        return 'In: {}, Out: {}'.format(
            len(self.get_next_game_players_list()),
            len(self.get_outage_players_list()))

    def get_outage_players_list(self):
        return self.get_outage_list().get('players', [])

    def get_next_game_attendees(self):
        attendees = ', '.join(self.get_next_game_players_list())
        outage = ', '.join(self.get_outage_players_list())
        return 'In: {},\r\nOut: {}'.format(attendees, outage)

    def get_next_game_players_list(self):
        return self.get_next_game().get('players', [])
