import shutil, random, os, sys

if __name__ == "__main__":
    labels = {
        "directory": "../yolo_labels",
        "train": "../dataset/labels/train",
        "validate": "../dataset/labels/val",
        "test": "../dataset/labels/test",
    }
    images = {
        "directory": "../videos/imgs/IMG_1756",
        "train": "../dataset/images/train",
        "validate": "../dataset/images/val",
        "test": "../dataset/images/test",
    }
    for file in os.listdir(labels["directory"]):
        if file == "classes.txt" or os.path.isdir(file):
            continue
        r = random.random()
        filename = os.path.splitext(file)[0]
        # image_file = os.path.join(images["directory"], filename + ".png")
        image_file = filename + ".png"
        if r < 0.7:
            shutil.move(os.path.join(labels["directory"], file), labels["train"])
            shutil.move(os.path.join(images["directory"], image_file), images["train"])
        elif r >= 0.7 and r < 0.9:
            shutil.move(os.path.join(labels["directory"], file), labels["validate"])
            shutil.move(os.path.join(images["directory"], image_file), images["validate"])
        else:
            shutil.move(os.path.join(labels["directory"], file), labels["test"])
            shutil.move(os.path.join(images["directory"], image_file), images["test"])
