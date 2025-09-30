import sys
import random
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QTabWidget, QPushButton, QComboBox, QSlider,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QGraphicsColorizeEffect,
    QMessageBox, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QImage, QPainter
from PyQt5.QtCore import Qt, QPointF, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import os
from ultralytics import YOLO
import tempfile

IMG_DIR = Path(r".\videos\imgs")
# VID_DIR = Path(r".\videos\vids_mp4")
VID_DIR = Path(r".\videos\vids_avi")
MOSQUITO_PATH = Path(r".\resources\mosquito.png")
TEAMMATES_DIR = Path(r".\resources\teammates")
EXPORT_DIR = Path(r".\tmp")
EXPORT_DIR.mkdir(exist_ok=True)

class BraggsPeakTab(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout()  # side-by-side layout
        self.setLayout(layout)

        # Left side: explanatory text
        text_label = QLabel(
            "<h2>Why Our Project Matters</h2>"
            "<p>Radiation therapy is a powerful tool in modern medicine, "
            "but conventional X-rays deposit energy along their entire path, "
            "damaging both healthy tissue and tumors.</p>"
            "<p>Protons behave differently — they release most of their energy "
            "at a precise depth, known as the <b>Bragg Peak</b>. "
            "This means we can target tumors more accurately while sparing "
            "surrounding healthy tissue.</p>"
            "<p>Our project leverages this principle to design better "
            "treatment planning and visualization tools, "
            "helping clinicians improve outcomes and reduce side effects.</p>"
        )
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignTop)
        text_label.setMinimumWidth(300)
        layout.addWidget(text_label, stretch=1)

        # Right side: Bragg’s Peak image
        img_path = Path(r".\resources\braggs_peak.png")
        if not img_path.exists():
            raise FileNotFoundError(f"Bragg's Peak image not found: {img_path}")
        pixmap = QPixmap(str(img_path))

        img_label = QLabel()
        img_label.setPixmap(pixmap.scaledToWidth(400, Qt.SmoothTransformation))
        img_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(img_label, stretch=1)

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
        self.current_image_path = None
        self.images = list(IMG_DIR.glob("*/*.png"))
        if not self.images:
            raise FileNotFoundError(f"No images found in {IMG_DIR}")

        self.teammates = list(TEAMMATES_DIR.glob("*.png"))
        self.teammate_index = 0

        # --- MAIN LAYOUT ---
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Top: image display
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        # Right: buttons/sliders
        controls_layout = QVBoxLayout()
        self.show_button = QPushButton("Show Random Image")
        self.show_button.clicked.connect(self.show_random_image)
        controls_layout.addWidget(self.show_button)

        self.add_mosquito_button = QPushButton("Add Mosquito")
        self.add_mosquito_button.clicked.connect(self.add_mosquito)
        controls_layout.addWidget(self.add_mosquito_button)

        self.add_teammates_button = QPushButton("Add Teammates")
        self.add_teammates_button.clicked.connect(self.add_teammates)
        controls_layout.addWidget(self.add_teammates_button)

        controls_layout.addWidget(QLabel("Adjust color tint strength"))
        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 100)
        self.brightness_slider.setValue(50)
        self.brightness_slider.valueChanged.connect(self.update_brightness)
        controls_layout.addWidget(self.brightness_slider)

        self.reset_button = QPushButton("Reset Image")
        self.reset_button.clicked.connect(self.reset_image)
        controls_layout.addWidget(self.reset_button)

        self.run_button = QPushButton("Run Detection")
        self.run_button.clicked.connect(self.run_detection)
        controls_layout.addWidget(self.run_button)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.view, stretch=3)
        top_layout.addLayout(controls_layout, stretch=1)
        main_layout.addLayout(top_layout, stretch=5)

        # Bottom: metadata area
        self.metadata_label = QLabel("Metadata will appear here.")
        self.metadata_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(self.metadata_label, stretch=1)

        self.image_pixmap_item = None
        self.brightness_effect = None

    # ----------------- Methods -----------------
    def reset_image(self):
        self.brightness_slider.setEnabled(True)
        if not self.current_image_path:
            return
        self.scene.clear()
        self.teammate_index = 0
        self.brightness_slider.setValue(50)

        pixmap = QPixmap(str(self.current_image_path))
        view_size = self.view.viewport().size()
        if view_size.width() <= 0 or view_size.height() <= 0:
            view_size = self.view.size()
        pixmap = pixmap.scaled(view_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.image_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.image_pixmap_item.setZValue(0)
        self.scene.addItem(self.image_pixmap_item)

        rect = self.image_pixmap_item.boundingRect()
        self.scene.setSceneRect(rect)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

        self.brightness_effect = QGraphicsColorizeEffect()
        self.brightness_effect.setColor(Qt.white)
        self.brightness_effect.setStrength(0.0)
        self.image_pixmap_item.setGraphicsEffect(self.brightness_effect)

        self.metadata_label.setText(f"Reset image: {self.current_image_path.name}")

    def show_random_image(self):
        self.brightness_slider.setEnabled(True)
        img_path = random.choice(self.images)
        self.current_image_path = img_path  # <-- store original path
        pixmap = QPixmap(str(img_path))
        self.scene.clear()
        self.teammate_index = 0
        self.brightness_slider.setValue(50)

        view_size = self.view.viewport().size()
        if view_size.width() <= 0 or view_size.height() <= 0:
            view_size = self.view.size()
        pixmap = pixmap.scaled(view_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.image_pixmap_item = QGraphicsPixmapItem(pixmap)
        self.image_pixmap_item.setZValue(0)
        self.scene.addItem(self.image_pixmap_item)

        rect = self.image_pixmap_item.boundingRect()
        self.scene.setSceneRect(rect)
        self.view.fitInView(rect, Qt.KeepAspectRatio)

        self.brightness_effect = QGraphicsColorizeEffect()
        self.brightness_effect.setColor(Qt.white)
        self.brightness_effect.setStrength(0.0)
        self.image_pixmap_item.setGraphicsEffect(self.brightness_effect)

        self.metadata_label.setText(f"Loaded image: {img_path.name}")

    def update_brightness(self, value: int):
        # Check if the pixmap item still exists
        try:
            if not self.image_pixmap_item or self.image_pixmap_item.scene() is None:
                return
        except RuntimeError:
            # The object was deleted
            return

        effect = self.image_pixmap_item.graphicsEffect()
        if not effect or not isinstance(effect, QGraphicsColorizeEffect):
            return

        strength = (value - 50) / 50.0
        if strength >= 0:
            effect.setColor(Qt.white)
            effect.setStrength(min(max(strength, 0.0), 1.0))
        else:
            effect.setColor(Qt.black)
            effect.setStrength(min(max(-strength, 0.0), 1.0))



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
        y = rect.height() * 0.35 - (teammate_pixmap.height() / 2)

        teammate_item = DraggablePixmapItem(teammate_pixmap, self.image_pixmap_item)
        teammate_item.setPos(QPointF(max(x, 0), max(y, 0)))
        teammate_item.setZValue(1)
        self.scene.addItem(teammate_item)

        self.teammate_index += 1

    def run_detection(self):
        
        if self.image_pixmap_item is None:
            return

        rect = self.image_pixmap_item.boundingRect()
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        self.scene.render(painter, target=rect, source=rect)
        painter.end()
        export_path = EXPORT_DIR / "exported_image.png"
        image.save(str(export_path))

        model_path = Path(r".\model\best.pt")
        model = YOLO(str(model_path))
        results = model.predict(
            source=str(export_path),
            save=True,
            project=str(EXPORT_DIR),
            name="yolo_results",
            exist_ok=True
        )

        save_dir = Path(results[0].save_dir)
        pred_file = save_dir / export_path.name
        if not pred_file.exists():
            candidates = list(save_dir.glob("*.*"))
            if not candidates:
                QMessageBox.warning(self, "YOLO Error", "No prediction image was generated.")
                return
            pred_file = candidates[-1]

        pred_pixmap = QPixmap(str(pred_file))
        self.scene.clear()
        self.image_pixmap_item = QGraphicsPixmapItem(pred_pixmap)
        self.scene.addItem(self.image_pixmap_item)
        self.scene.setSceneRect(self.image_pixmap_item.boundingRect())
        self.view.fitInView(self.image_pixmap_item.boundingRect(), Qt.KeepAspectRatio)

        self.metadata_label.setText(f"Prediction displayed from {pred_file.name}")

        self.brightness_slider.setEnabled(False)


class VideoTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.dropdown = QComboBox()
        self.videos = list(VID_DIR.glob("*.avi"))
        # self.videos = list(VID_DIR.glob("*.mp4"))
        if not self.videos:
            raise FileNotFoundError(f"No .avi files found in {VID_DIR}")
            # raise FileNotFoundError(f"No .mp4 files found in {VID_DIR}")
        for v in self.videos:
            self.dropdown.addItem(v.name, str(v))
        self.layout.addWidget(self.dropdown)

        self.video_widget = QVideoWidget()
        self.layout.addWidget(self.video_widget, stretch=1)

        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)
        self.dropdown.currentIndexChanged.connect(self.play_selected_video)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.play_pause)
        self.layout.addWidget(self.play_button)
        if self.videos:
            self.play_selected_video(0)

    def play_selected_video(self, index):
        if index < 0:
            return
        video_path = self.dropdown.itemData(index)

        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.player.play()
        self.player.pause()
        self.play_button.setText("Play")

    def play_pause(self, index):
        if index < 0:
            return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.play_button.setText("Play")
        else:
            self.player.play()
            self.play_button.setText("Pause")



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
        self.tabs.addTab(BraggsPeakTab(), "Method 3")
        self.tabs.addTab(DemoTab("Content for Method 4"), "Method 4")
        self.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
