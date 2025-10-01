## Automatic Detection of Range Shifter Board Prior to Proton Beam Delivery



# Steps
1. Place all videos in videos/videos
2. Place all label .txts in yolo_labels, in their respective folders (ex. IMG_1800_yolo_labels)
3. Modify and run movToPng to create frames
4. Modify and run generateEmptyTxt if you have any videos with no objects tracked at all
5. Modify and run renameLabels to rename your label files and place them all in the correct folder. Make sure combined is empty before running
6. Modify and run makeTestData to place images in correct folder, and then move everything to the dataset folder

# Important
- The label files must be named like "frame_000013.txt", or "IMG_1830frame_000013.txt"