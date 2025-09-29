import sys
import random
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QTabWidget, QPushButton, QComboBox, QSlider,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QGraphicsColorizeEffect,
    QMessageBox
)
from PyQt5.QtGui import QPixmap, QImage, QPainter
from PyQt5.QtCore import Qt, QPointF, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import os

IMG_DIR = Path(r"C:\Users\jzhang29\Projects\Archive\KIDS25-Team3\videos\imgs")
VID_DIR = Path(r"C:\Users\jzhang29\Projects\Archive\KIDS25-Team3\videos\vids_mp4")
MOSQUITO_PATH = Path(r"C:\Users\jzhang29\Projects\Archive\KIDS25-Team3\resources\mosquito.png")
TEAMMATES_DIR = Path(r"C:\Users\jzhang29\Projects\Archive\KIDS25-Team3\resources\teammates")
EXPORT_DIR = Path(r".\tmp")
EXPORT_DIR.mkdir(exist_ok=True)


class DraggablePixmapItem(QGraphicsPixmapItem):
    def __init__(self, pixmap: QPixmap, boundary_item: QGraphicsPixmapItem):
        super().__init__(pixmap)
        self.boundary_item = boundary_item
        self.setFlags(QGraphicsPixmapItem.ItemIsMovable | QGraphicsPixmapItem.ItemIsSelectable)
        # ensure itemChange receives position updates
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and self.scene():
            new_pos = value
            rect = self.boundary_item.boundingRect()
            w = self.boundingRect().width()
            h = self.boundingRect().height()
            # clamp position so item stays fully inside the boundary rect
            x = min(max(new_pos.x(), 0), max(0, rect.width() - w))
            y = min(max(new_pos.y(), 0), max(0, rect.height() - h))
            return QPointF(x, y)
        return super().itemChange(change, value)


class ImageTab(QWidget):
    def __init__(self):
        super().__init__()
        self.images = list(IMG_DIR.glob("*/*.png"))
        if not self.images:
            raise FileNotFoundError(f"No images found in {IMG_DIR}")

        self.teammates = list(TEAMMATES_DIR.glob("*.png"))
        self.teammate_index = 0

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.layout.addWidget(self.view, stretch=1)

        self.image_pixmap_item = None
        self.brightness_effect = None

        # Buttons
        self.show_button = QPushButton("Show Random Image")
        self.show_button.clicked.connect(self.show_random_image)
        self.layout.addWidget(self.show_button)

        self.add_mosquito_button = QPushButton("Add Mosquito")
        self.add_mosquito_button.clicked.connect(self.add_mosquito)
        self.layout.addWidget(self.add_mosquito_button)

        self.add_teammates_button = QPushButton("Add Teammates")
        self.add_teammates_button.clicked.connect(self.add_teammates)
        self.layout.addWidget(self.add_teammates_button)

        # Brightness slider (fast because it uses a graphics effect)
        self.layout.addWidget(QLabel("Adjust Brightness"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)  # neutral
        self.brightness_slider.valueChanged.connect(self.update_brightness)
        self.layout.addWidget(self.brightness_slider)

        self.export_button = QPushButton("Export Image")
        self.export_button.clicked.connect(self.export_image)
        self.layout.addWidget(self.export_button)

    def show_random_image(self):
        img_path = random.choice(self.images)
        pixmap = QPixmap(str(img_path))
        self.scene.clear()
        self.teammate_index = 0
        self.brightness_slider.setValue(50)

        # Scale image to fit view while keeping aspect ratio (fills view as best possible)
        view_size = self.view.viewport().size()
        if view_size.width() <= 0 or view_size.height() <= 0:
            # fallback if view hasn't been shown yet
            view_size = self.view.size()
        pixmap = pixmap.scaled(view_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.image_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.image_pixmap_item.setZValue(0)
        self.scene.addItem(self.image_pixmap_item)

        # ensure scene rect matches image so coordinates align and boundary checks work
        rect = self.image_pixmap_item.boundingRect()
        self.scene.setSceneRect(rect)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

        # Reset and attach brightness effect
        self.brightness_effect = QGraphicsColorizeEffect()
        self.brightness_effect.setColor(Qt.white)
        self.brightness_effect.setStrength(0.0)
        self.image_pixmap_item.setGraphicsEffect(self.brightness_effect)

    def update_brightness(self, value: int):
        if not self.brightness_effect:
            return
        # slider value 50 -> neutral; (0..100) maps to -1..+1
        strength = (value - 50) / 50.0
        if strength >= 0:
            self.brightness_effect.setColor(Qt.white)
            self.brightness_effect.setStrength(min(max(strength, 0.0), 1.0))
        else:
            self.brightness_effect.setColor(Qt.black)
            self.brightness_effect.setStrength(min(max(-strength, 0.0), 1.0))

    def add_mosquito(self):
        if self.image_pixmap_item is None:
            return
        mosquito_pixmap = QPixmap(str(MOSQUITO_PATH))
        mosquito_item = DraggablePixmapItem(mosquito_pixmap, self.image_pixmap_item)

        rect = self.image_pixmap_item.boundingRect()
        x = random.uniform(0, max(0, rect.width() - mosquito_pixmap.width()))
        y = random.uniform(0, max(0, rect.height() - mosquito_pixmap.height()))
        mosquito_item.setPos(QPointF(x, y))
        mosquito_item.setZValue(1)
        self.scene.addItem(mosquito_item)

    def add_teammates(self):
        if self.image_pixmap_item is None or not self.teammates:
            return

        if self.teammate_index >= len(self.teammates):
            QMessageBox.information(self, "Limit Reached", "Max number of teammates image reached")
            return

        teammate_path = self.teammates[self.teammate_index]
        teammate_pixmap = QPixmap(str(teammate_path))

        rect = self.image_pixmap_item.boundingRect()
        spacing = rect.width() / (len(self.teammates) + 1)
        x = spacing * (self.teammate_index + 1) - (teammate_pixmap.width() / 2)
        # slightly lower placement (about 1/3 of the image)
        y = rect.height() * 0.35 - (teammate_pixmap.height() / 2)

        teammate_item = DraggablePixmapItem(teammate_pixmap, self.image_pixmap_item)
        teammate_item.setPos(QPointF(max(x, 0), max(y, 0)))
        teammate_item.setZValue(1)
        self.scene.addItem(teammate_item)

        self.teammate_index += 1

    def export_image(self):
        if self.image_pixmap_item is None:
            return
        rect = self.image_pixmap_item.boundingRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        # Render the scene (including graphics effects) into the QImage
        self.scene.render(painter, target=rect, source=rect)
        painter.end()
        export_path = EXPORT_DIR / "exported_image.png"
        image.save(str(export_path))
        print(f"Image exported to {export_path}")


class VideoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.dropdown = QComboBox()
        self.videos = list(VID_DIR.glob("*.mp4"))
        if not self.videos:
            raise FileNotFoundError(f"No .mp4 files found in {VID_DIR}")
        for v in self.videos:
            self.dropdown.addItem(v.name, str(v))
        self.layout.addWidget(self.dropdown)

        self.video_widget = QVideoWidget()
        self.layout.addWidget(self.video_widget, stretch=1)

        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)
        self.dropdown.currentIndexChanged.connect(self.play_selected_video)

        if self.videos:
            self.play_selected_video(0)

    def play_selected_video(self, index):
        if index < 0:
            return
        video_path = self.dropdown.itemData(index)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.player.play()


class DemoTab(QWidget):
    def __init__(self, text):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel(text))
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hackathon Demo GUI")
        self.setGeometry(200, 200, 1000, 800)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(ImageTab(), "Method 1")
        self.tabs.addTab(VideoTab(), "Method 2")
        self.tabs.addTab(DemoTab("Content for Method 3"), "Method 3")
        self.tabs.addTab(DemoTab("Content for Method 4"), "Method 4")
        self.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
