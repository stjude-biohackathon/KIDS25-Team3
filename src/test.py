from ultralytics import YOLO

if __name__ == "__main__":
    model = YOLO("../model/runs/detect/train/weights/best.pt")
    results = model.predict("../videos/videos/IMG_1830.mov", save=True)
    print(results)