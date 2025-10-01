import sys
import random
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QTabWidget, QPushButton, QComboBox, QSlider,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QGraphicsColorizeEffect,
    QMessageBox, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QMovie
from PyQt5.QtCore import Qt, QPointF, QUrl, QSize
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
import os
from ultralytics import YOLO
import tempfile
import cv2
from PyQt5.QtCore import QTimer, Qt
import time

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
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0,0)
        self.slider.sliderMoved.connect(self.set_position)

        self.timestamp = QLabel("00:00/00:00")

        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)

        self.progress_layout = QHBoxLayout()
        self.progress_layout.addWidget(self.slider)
        self.progress_layout.addWidget(self.timestamp)

        self.tools_layout = QHBoxLayout()
        self.tools_layout.addWidget(self.play_button)
        self.tools_layout.addLayout(self.progress_layout)

        self.layout.addLayout(self.tools_layout)
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

    def update_position(self, position):
        self.slider.setValue(position)
        self.update_timestamp(position)

    def update_duration(self, duration):
        self.slider.setRange(0, duration)
        self.total_duration = duration
        self.update_timestamp(self.player.position())

    def set_position(self, position):
        self.player.setPosition(position)

    def update_timestamp(self, current_ms):
        def ms_to_time(ms):
            seconds = ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes:02}:{seconds:02}"

        current_time = ms_to_time(current_ms)
        total_time = ms_to_time(self.player.duration())
        self.timestamp.setText(f"{current_time} / {total_time}")

class VideoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.model = YOLO("model/best.pt")

        self.setWindowTitle("OpenCV Video in PyQt5")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)

        self.rs_board_detected = False
        self.results = QLabel(str(self.rs_board_detected))
        self.results.setAlignment(Qt.AlignCenter)

        self.pass_icon = QPixmap("resources/Green_check.svg")
        self.pass_icon = self.pass_icon.scaled(100, 100)
        self.fail_icon = QPixmap("resources/Red_x.png")
        self.fail_icon = self.fail_icon.scaled(100, 100)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.results)
        self.setLayout(layout)

        self.update_result()

        # OpenCV VideoCapture
        self.cap = cv2.VideoCapture(0)  # 0 = default camera

        # Timer to grab frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~30 fps

    def update_result(self):
        if self.rs_board_detected:
            self.results.setPixmap(self.pass_icon)
        else:
            self.results.setPixmap(self.fail_icon)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            # Convert BGR (OpenCV) to RGB (Qt expects RGB)
            results = self.model(frame, conf=0.25, verbose=False, device='cpu')
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            if len(results) > 0 and results[0].boxes is not None:
                
                boxes = results[0].boxes

                if not boxes:
                    self.rs_board_detected = False
                    
                for box in boxes:
                    self.rs_board_detected = True
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    label = f"RS Board: {conf:.2f}"
                    cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            self.update_result()
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.label.setPixmap(QPixmap.fromImage(qt_img))

    def closeEvent(self, event):
        self.cap.release()
        super().closeEvent(event)


class DemoTab(QWidget):
    def __init__(self, text):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel(text))
        self.setLayout(self.layout)

class ModelTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.p1 = QLabel(
            "<p>Our computer vision specialists created a custom GUI for labelling foreground "
            "and background points before submission to SAM2 to create a 3D-annotated model, "
            "shown below </p>"
        )
        self.p1.setAlignment(Qt.AlignHCenter)

        self.im1 = QHBoxLayout()
        gui_path = Path(r".\resources\manual_gui.png")
        if not gui_path.exists():
            raise FileNotFoundError(f"Manual GUI image not found: {gui_path}")
        gui_pixmap = QPixmap(str(gui_path))

        gui_label = QLabel()
        gui_label.setPixmap(gui_pixmap.scaledToWidth(400, Qt.SmoothTransformation))

        sam2_label = QLabel()
        sam2_path = Path(r".\resources\sam2.gif")
        if not sam2_path.exists():
            raise FileNotFoundError(f"SAM2 image not found: {sam2_path}")
        sam2_label.setPixmap(QPixmap(str(sam2_path)).scaledToWidth(400, Qt.SmoothTransformation))

        scaling = gui_label.geometry()
        movie_size = QSize(scaling.width()//2,scaling.height()//2)
        self.sam2_movie = QMovie(str(sam2_path))
        sam2_label.setMovie(self.sam2_movie)
        self.sam2_movie.setScaledSize(movie_size)
        self.sam2_movie.setSpeed(200)
        self.sam2_movie.start()

        self.im1.addWidget(gui_label)
        self.im1.addWidget(sam2_label)
        self.im1.setAlignment(Qt.AlignCenter)

        self.p2 = QLabel(
            "<p> Next, we trained a YOLO model on our collected data using the "
            "Ultralytics YOLOv11 framework, "
            "with the results of our training plotted below.</p>"
        )
        self.p2.setAlignment(Qt.AlignCenter)

        self.im2 = QHBoxLayout()
        results_label = QLabel()
        results_path = Path(r".\resources\results.png")
        if not results_path.exists():
            raise FileNotFoundError(f"SAM2 image not found: {results_path}")
        results_label.setPixmap(QPixmap(str(results_path)).scaledToWidth(600, Qt.SmoothTransformation))
        self.im2.addWidget(results_label)
        self.im2.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.p1)
        self.layout.addLayout(self.im1)
        self.layout.addWidget(self.p2)
        self.layout.addLayout(self.im2)


        self.setLayout(self.layout)
        # SAM2 for annotation, using a custom gui to determin foreground/background points
        # trained on YOLO model




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hackathon Demo GUI")
        self.setGeometry(200, 200, 1000, 800)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(ImageTab(), "Picture")
        self.tabs.addTab(VideoTab(), "Video")
        self.tabs.addTab(BraggsPeakTab(), "Physics")
        self.tabs.addTab(ModelTab(), "Model")
        self.tabs.addTab(VideoWidget(), "Real-time")
        self.showMaximized()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
