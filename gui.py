import sys
import random
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QTabWidget, QPushButton, QComboBox
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget


IMG_DIR = Path(r"C:\Users\jzhang29\Projects\Archive\KIDS25-Team3\videos\imgs")
VID_DIR = Path(r"C:\Users\jzhang29\Projects\Archive\KIDS25-Team3\videos\vids_mp4")


# ---------------- Tab 1: Image Viewer ----------------
class ImageTab(QWidget):
    def __init__(self):
        super().__init__()

        # Collect all images from subfolders
        self.images = list(IMG_DIR.glob("*/*.png"))
        if not self.images:
            raise FileNotFoundError(f"No images found in {IMG_DIR}")

        # Layout
        self.layout = QVBoxLayout()

        # Image display
        self.image_label = QLabel("Click the button to show an image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(True)  # auto resize
        self.layout.addWidget(self.image_label, stretch=1)

        # Button
        self.button = QPushButton("Show Random Image")
        self.button.clicked.connect(self.show_random_image)
        self.layout.addWidget(self.button)

        self.setLayout(self.layout)

    def show_random_image(self):
        img_path = random.choice(self.images)
        pixmap = QPixmap(str(img_path))
        self.image_label.setPixmap(pixmap)


# ---------------- Tab 2: Video Player ----------------
class VideoTab(QWidget):
    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout()

        # Dropdown for video selection
        self.dropdown = QComboBox()
        self.videos = list(VID_DIR.glob("*.mp4"))
        if not self.videos:
            raise FileNotFoundError(f"No .mov files found in {VID_DIR}")

        # Add video names to dropdown
        for v in self.videos:
            self.dropdown.addItem(v.name, str(v))

        self.layout.addWidget(self.dropdown)

        # Video display
        self.video_widget = QVideoWidget()
        self.layout.addWidget(self.video_widget, stretch=1)

        # Media player
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)

        # Connect dropdown selection
        self.dropdown.currentIndexChanged.connect(self.play_selected_video)

        self.setLayout(self.layout)

    def play_selected_video(self, index):
        if index < 0:
            return
        video_path = self.dropdown.itemData(index)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.player.play()


# ---------------- Other Tabs ----------------
class DemoTab(QWidget):
    def __init__(self, text):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(text))
        self.setLayout(layout)


# ---------------- Main Window ----------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hackathon Demo GUI")
        self.setGeometry(200, 200, 800, 600)

        # Create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: Image viewer
        self.tabs.addTab(ImageTab(), "Method 1")

        # Tab 2: Video player
        self.tabs.addTab(VideoTab(), "Method 2")

        # Other placeholder tabs
        self.tabs.addTab(DemoTab("Content for Method 3"), "Method 3")
        self.tabs.addTab(DemoTab("Content for Method 4"), "Method 4")

        # Start maximized
        self.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
