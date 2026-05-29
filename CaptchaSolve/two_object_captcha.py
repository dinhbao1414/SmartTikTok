
# import matplotlib.pyplot as plt
import numpy as np
import torch
import sys
import os
import cv2
import torchvision.transforms as transforms
sys.path.append(os.getcwd())
from CaptchaSolve.ops import non_max_suppression, resize_and_pad_image, scale_boxes
# from ultralytics import YOLO


class YoloCaptchaV2:
    def __init__(self, weight_path):
        self.torch_script_model = torch.jit.load(weight_path)

    def find_most_similar_characters(self,  image, show=False):

        if isinstance(image, str):
        # Read the image
            image = cv2.imread(image)
        original_image = image.copy()
        image = resize_and_pad_image(image)
        # image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Kích thước ảnh đã resize
        # resized_width = 640
        # resized_height = 640
        # image= cv2.resize(image,(resized_height,resized_width))


        # Define a transform to convert the image to tensor
        transform = transforms.ToTensor()

        # Convert the image to PyTorch tensor
        tensor = transform(image)

        preds = self.torch_script_model(tensor.unsqueeze(0))
        # preds = self.model(tensor.unsqueeze(0))

        data = non_max_suppression(preds,
                                   0.25,
                                    0.7,
                                    agnostic=False,
                                    max_det=300,
                                    classes=None)[0].numpy()
        data[:,5].astype(int)
        data[:,:4] = scale_boxes(image.shape, data[:,:4], original_image.shape)
        # results = self.model.predict(image)
        # for result in results:
        #     boxes = result.boxes  # Boxes object for bbox outputs
        #     masks = result.masks  # Masks object for segmentation masks outputs
        #     keypoints = result.keypoints  # Keypoints object for pose outputs
        #     probs = result.probs  # Class probabilities for classification outputs
        # res_plotted = results[0].plot()
        # data = results[0].boxes.data.numpy()
        # Tìm các nhãn xuất hiện ít nhất 2 lần
        unique_labels, label_counts = np.unique(data[:, -1], return_counts=True)
        labels_appearing_twice = unique_labels[label_counts >= 2]
        try:
            # Trích xuất tâm của các bounding box tương ứng với các nhãn xuất hiện ít nhất 2 lần
            center_points = []
            for label in labels_appearing_twice:
                label_indices = np.where(data[:, -1] == label)[0]
                label_bboxes = data[label_indices, :4]
                label_center_x = ((label_bboxes[:, 0] + label_bboxes[:, 2]) / 2).astype(int)
                label_center_y = ((label_bboxes[:, 1] + label_bboxes[:, 3]) / 2).astype(int)
                label_centers = np.stack((label_center_x, label_center_y), axis=-1)
                center_points.append(label_centers)

            center_points = np.vstack(center_points)[:2]

            # Kích thước ảnh gốc
            original_height, original_width = original_image.shape[:2]

            # # Tính toán tỷ lệ giữa ảnh gốc và ảnh đã resize
            # scale_x = original_width / resized_width
            # scale_y = original_height / resized_height

            # # Tính toán lại tọa độ center points trên ảnh gốc
            # center_points = center_points * np.array([scale_x, scale_y])

            # if show:
            #     plt.imshow(image)
            #     plt.scatter(center_points[:, 0], center_points[:, 1], c='red', marker='x')
            #     plt.show()
            return center_points.astype(int)

        except:
            # if show:
            #     plt.imshow(image)
            #     plt.show()
            return False