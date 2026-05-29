import cv2, numpy as np

class PuzleSolver:
    def __init__(self, size_slide, size_bg, img_slide, img_bg):
        self.size_slide = size_slide
        self.size_bg = size_bg
        self.img_slide = img_slide
        self.img_bg  = img_bg


    def get_position(self):

        self.img_bg  = cv2.resize(self.img_bg , self.size_bg, interpolation = cv2.INTER_LINEAR)
        self.img_slide = cv2.resize(self.img_slide, self.size_slide, interpolation = cv2.INTER_LINEAR)

        img = self.__sobel_operator(self.img_slide)
        background = self.__sobel_operator(self.img_bg)

        res = cv2.matchTemplate(img, background, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.28)
        data = list(zip(*loc[::-1]))
        is_match = len(data) > 0
        if is_match:
            w, h = img.shape[1], img.shape[0]
            x, y = data[0][0] + int(w / 2), data[0][1]
            cv2.rectangle(self.img_bg, (x, y), (x + int(w / 2), y + h), (255,0,0), 1)
            return x
        else:
            return False

    def __sobel_operator(self, img_path):
        scale = 1
        delta = 0
        ddepth = cv2.CV_16S
        img = cv2.GaussianBlur(img_path, (3, 3), 0)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        grad_x = cv2.Sobel(gray, ddepth, 1, 0, ksize=3, scale=scale, delta=delta, borderType=cv2.BORDER_DEFAULT)
        grad_y = cv2.Sobel(gray, ddepth, 0, 1, ksize=3, scale=scale, delta=delta, borderType=cv2.BORDER_DEFAULT)
        abs_grad_x = cv2.convertScaleAbs(grad_x)
        abs_grad_y = cv2.convertScaleAbs(grad_y)
        grad = cv2.addWeighted(abs_grad_x, 0.5, abs_grad_y, 0.5, 0)
        return grad