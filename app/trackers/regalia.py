from app.trackers.base import BaseTracker


class RegaliaTracker(BaseTracker):

    def __init__(self):
        super().__init__(
            name="Prismatic Champion's Regalia",
            data_filename="regalia.json"
        )