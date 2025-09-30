from ultralytics import YOLO

if __name__ == "__main__":
    model = YOLO("../model/runs/detect/train/weights/best.pt")
    results = model.predict("../IMG_1825.mov", save=True)
    print(results)