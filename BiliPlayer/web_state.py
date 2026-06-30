"""Thread-safe shared state bridging the web server and player threads."""

from __future__ import annotations

import threading


class SharedState:
    """Thread-safe state shared between web server (Flask) and player (asyncio).

    - Player writes playback status fields; web server reads them for API responses.
    - Web server enqueues commands; player dequeues and executes them.
    - Playlist mutations are protected by a lock since lists are not GIL-atomic.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # ---- Playback status (written by player callbacks, read by web) ----
        self.current_bv: str = ""
        self.current_title: str = ""
        self.current_time: float = 0.0
        self.duration: float = 0.0
        self.volume: int = 30
        self.is_playing: bool = True

        # ---- Playlist ----
        self.playlist: list = []          # list of BV id strings
        self.current_index: int = -1       # index in playlist of current_bv

        # ---- User info ----
        self.uid: int = 0
        self.fav_name: str = ""

        # ---- Play mode ----
        self.play_mode: str = "shuffle"   # 'sequential' | 'shuffle' | 'repeat_one'

        # ---- Command queue (single-slot; web writes, player reads-and-clears) ----
        self._cmd: str | None = None
        self._cmd_value = None

        # ---- Reload flag (web writes, play_main monitor reads-and-clears) ----
        self._reload_pending: bool = False

    # ------------------------------------------------------------------
    # Command helpers
    # ------------------------------------------------------------------

    def set_command(self, cmd: str, value=None) -> None:
        with self._lock:
            self._cmd = cmd
            self._cmd_value = value

    def get_command(self) -> tuple | None:
        with self._lock:
            if self._cmd is None:
                return None
            cmd = (self._cmd, self._cmd_value)
            self._cmd = None
            self._cmd_value = None
            return cmd

    def mark_reload(self) -> None:
        with self._lock:
            self._reload_pending = True

    def needs_reload(self) -> bool:
        with self._lock:
            flag = self._reload_pending
            self._reload_pending = False
        return flag

    # ------------------------------------------------------------------
    # Playlist helpers (lock-protected)
    # ------------------------------------------------------------------

    def set_playlist(self, bv_list: list) -> None:
        with self._lock:
            self.playlist = list(bv_list)
            self.current_index = 0 if bv_list else -1

    def add_to_playlist(self, bvid: str) -> None:
        with self._lock:
            self.playlist.append(bvid)

    def remove_from_playlist(self, index: int) -> bool:
        with self._lock:
            if 0 <= index < len(self.playlist):
                self.playlist.pop(index)
                if index < self.current_index:
                    self.current_index -= 1
                elif index == self.current_index:
                    if self.current_index >= len(self.playlist):
                        self.current_index = len(self.playlist) - 1
                return True
            return False

    def reorder_playlist(self, from_idx: int, to_idx: int) -> bool:
        with self._lock:
            n = len(self.playlist)
            if not (0 <= from_idx < n and 0 <= to_idx < n):
                return False
            item = self.playlist.pop(from_idx)
            self.playlist.insert(to_idx, item)
            if from_idx == self.current_index:
                self.current_index = to_idx
            elif from_idx < self.current_index and to_idx >= self.current_index:
                self.current_index -= 1
            elif from_idx > self.current_index and to_idx <= self.current_index:
                self.current_index += 1
            return True

    def get_playlist(self) -> list:
        with self._lock:
            return list(self.playlist)

    def get_current_index(self) -> int:
        with self._lock:
            return self.current_index

    def set_current_index(self, index: int) -> None:
        with self._lock:
            self.current_index = index

    # ------------------------------------------------------------------
    # Playback status update (called from player's timeupdate callback)
    # ------------------------------------------------------------------

    def update_playback(self, cur: float, total: float, bvid: str, title: str) -> None:
        self.current_time = cur
        self.duration = total
        self.current_bv = bvid
        self.current_title = title
        if bvid and bvid in self.playlist:
            self.current_index = self.playlist.index(bvid)

    def set_playing(self, playing: bool) -> None:
        self.is_playing = playing

    # ------------------------------------------------------------------
    # Snapshot for API responses
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "current_bv": self.current_bv,
                "current_title": self.current_title,
                "current_time": self.current_time,
                "duration": self.duration,
                "volume": self.volume,
                "is_playing": self.is_playing,
                "playlist": list(self.playlist),
                "current_index": self.current_index,
                "play_mode": self.play_mode,
                "uid": self.uid,
                "fav_name": self.fav_name,
            }
