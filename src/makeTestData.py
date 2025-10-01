import shutil, random, os, sys

def moveAll(path, dst):
    # Copy all pngs in path to videos/imgs/combined
    for f in os.listdir(path):
        p = os.path.join(path, f)   # videos/imgs/IMG.../IMG...frame000000.png
        if os.path.splitext(p)[1] == '.png':
            shutil.move(p, dst)

if __name__ == "__main__":
    labels = {
        "directory": "../yolo_labels/combined",
        "train": "../dataset/labels/train",
        "validate": "../dataset/labels/val",
        "test": "../dataset/labels/test",
    }
    images = {
        "directory": "../videos/imgs/combined",
        "train": "../dataset/images/train",
        "validate": "../dataset/images/val",
        "test": "../dataset/images/test",
    }
    os.makedirs(labels["train"], exist_ok=True)
    os.makedirs(labels["validate"], exist_ok=True)
    os.makedirs(labels["test"], exist_ok=True)
    os.makedirs(images["train"], exist_ok=True)
    os.makedirs(images["validate"], exist_ok=True)
    os.makedirs(images["test"], exist_ok=True)
    
    img_names = [
        "IMG_1756", "IMG_1824", "IMG_1831", "IMG_1832"
    ] # videos used to train/validate
    
    os.makedirs(images["directory"], exist_ok=True)
    parent_imgs = os.path.dirname(images["directory"]) # videos/imgs/
    for img in os.listdir(parent_imgs):
        if img in img_names:
            moveAll(os.path.join(parent_imgs, img), images["directory"]) # videos/imgs/IMG...
        
    for file in os.listdir(labels["directory"]):
        if file == "classes.txt" or os.path.isdir(file):
            continue
        r = random.random()
        filename = os.path.splitext(file)[0]
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
