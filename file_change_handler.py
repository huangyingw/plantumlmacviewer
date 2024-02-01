from watchdog.events import FileSystemEventHandler


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, viewer, filePath):
        super().__init__()
        self.viewer = viewer
        self.filePath = filePath

    def on_modified(self, event):
        if event.src_path == self.filePath:
            self.viewer.loadAndDisplayUML(self.filePath)
