from yandex_music import Client
from yandex_music.utils.captcha_response import CaptchaResponse
from yandex_music.rotor.station import Station
from yandex_music.rotor.station_tracks_result import StationTracksResult
from yandex_music.track.track import Track
from yandex_music.download_info import DownloadInfo

from random import randint

from typing import Callable, List, Optional


class Music:
    def __init__(self, token: Optional[str]=None, username: Optional[str]=None, password: Optional[str]=None, captcha_callback: Optional[Callable[[CaptchaResponse], str]]=None, station: Optional[str]="user:onyourwave") -> None:
        if captcha_callback:
            self._captcha_callback = captcha_callback

        if token:
            try:
                self._client: Client = Client.from_token(
                    token = token,
                    report_new_fields = False
                )

            except:
                if not username or not password:
                    raise Exception("No Yandex.Music account credentials")

                self._client: Client = Client.from_credentials(
                    username = username,
                    password = password,
                    captcha_callback = self._captcha_callback,
                    report_new_fields = False
                )

        else:
            if not username or not password:
                raise Exception("No Yandex.Music account credentials")

            self._client: Client = Client.from_credentials(
                username = username,
                password = password,
                captcha_callback = self._captcha_callback,
                report_new_fields = False
            )

        self.station: Station = self._client.rotor_station_info(
            station = "user:onyourwave"
        )[0].station

        self.station_id: str = "{type_}:{tag}".format(
            type_ = self.station.id.type,
            tag = self.station.id.tag
        )

        self.station_from: str = self.station.id_for_from

        self.play_id: str = None
        self.index: int = 0
        self.current_track: Track = None
        self.station_tracks: StationTracksResult = None
        self.on_replay: bool = False
        self.is_playing_track: bool = False

    def _captcha_callback(self, captcha: CaptchaResponse) -> str:
        return input(
            "{captcha}\nEnter captcha: ".format(
                captcha = captcha.x_captcha_url
            )
        )

    def search_tracks(self, query: str) -> List[Track]:
        return self._client.search(
            text = query,
            type_ = "track"
        ).tracks.results

    def track_download_url(self, track: Track) -> str:
        download_info: DownloadInfo = sorted(
            filter(
                self._sort_tracks_codec,
                track.get_download_info()
            ),
            key=self._sort_tracks_kbps
        )[0]

        return download_info.get_direct_link()

    def _sort_tracks_codec(self, download_info: DownloadInfo) -> bool:
        return download_info.codec == "mp3"

    def _sort_tracks_kbps(self, download_info: DownloadInfo) -> int:
        return -download_info.bitrate_in_kbps

    def start_radio(self) -> Track:
        self.station_id = self.station_id
        self.station_from = self.station_from

        self.__update_radio_batch()

        self.current_track = self.__update_current_track()

        return self.current_track

    def play_next(self) -> Track:
        self.__send_play_end_track(
            track = self.current_track,
            play_id = self.play_id
        )

        self.__send_play_end_radio(
            track = self.current_track,
            batch_id = self.station_tracks.batch_id
        )

        self.index += 1

        if self.index >= len(self.station_tracks.sequence):
            self.__update_radio_batch(
                queue = self.current_track.track_id
            )

        self.current_track: Track = self.__update_current_track()

        return self.current_track

    def __update_radio_batch(self, queue: Optional[str]=None):
        self.index: int = 0

        self.station_tracks: StationTracksResult = self._client.rotor_station_tracks(
            station = self.station_id,
            queue = queue
        )

        self.__send_start_radio(
            batch_id = self.station_tracks.batch_id
        )

    def __update_current_track(self) -> Track:
        self.play_id: str = self.__generate_play_id()

        track: List[Track] = self._client.tracks([
            self.station_tracks.sequence[self.index].track.track_id
        ])[0]

        self.__send_play_start_track(
            track = track,
            play_id = self.play_id
        )

        self.__send_play_start_radio(
            track = track,
            batch_id = self.station_tracks.batch_id
        )

        return track

    def __send_start_radio(self, batch_id: str):
        self._client.rotor_station_feedback_radio_started(
            station = self.station_id,
            from_ = self.station_from,
            batch_id = batch_id
        )

    def __send_play_start_track(self, track: Track, play_id: str):
        total_seconds: float = track.duration_ms / 1000

        self._client.play_audio(
            track_id = track.id,
            from_ = "desktop_win-home-playlist_of_the_day-playlist-default",
            album_id = track.albums[0].id,
            play_id = play_id,
            track_length_seconds = 0,
            total_played_seconds = 0,
            end_position_seconds = total_seconds,
        )

    def __send_play_start_radio(self, track: Track, batch_id: str):
        self._client.rotor_station_feedback_track_started(
            station = self.station_id,
            track_id = track.id,
            batch_id = batch_id
        )

    def __send_play_end_track(self, track: Track, play_id: str):
        played_seconds: float = track.duration_ms / 1000
        total_seconds: float = track.duration_ms / 1000

        self._client.play_audio(
            track_id = track.id,
            from_ = "desktop_win-home-playlist_of_the_day-playlist-default",
            album_id = track.albums[0].id,
            play_id = play_id,
            track_length_seconds = int(total_seconds),
            total_played_seconds = played_seconds,
            end_position_seconds = total_seconds,
        )

    def __send_play_end_radio(self, track: Track, batch_id: str):
        played_seconds: float = track.duration_ms / 1000

        self._client.rotor_station_feedback_track_finished(
            station = self.station_id,
            track_id = track.id,
            total_played_seconds = played_seconds,
            batch_id = batch_id
        )

    @staticmethod
    def __generate_play_id():
        return "%s-%s-%s" % (randint(1, 999), randint(1, 999), randint(1, 999))
