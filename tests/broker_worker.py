"""Controlled worker process used only by the real-broker fault suite."""

import os
import time
from pathlib import Path
from test_foundation import ControlledSource
import codeatlas.queue as queue


class InterruptibleSource(ControlledSource):
    def inventory(self, *args):
        marker = os.environ.get("CODEATLAS_TEST_CRASH_MARKER")
        if marker and not Path(marker).exists():
            Path(marker).write_text("entered inventory after persisted pin")
            time.sleep(30)
        return super().inventory(*args)


queue.GitHubSource = InterruptibleSource
if __name__ == "__main__":
    queue.app.worker_main(
        [
            "worker",
            "--pool=solo",
            "--concurrency=1",
            "--loglevel=WARNING",
            "--without-gossip",
            "--without-mingle",
            "--without-heartbeat",
            "-Q",
            os.environ["CODEATLAS_TEST_QUEUE"],
        ]
    )
