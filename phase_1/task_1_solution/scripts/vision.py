import cv2
import numpy as np

MASK = cv2.imread('../images/front_vision_mask_01.png', 0)
DEFAULT_SEG_CRT = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)


def mask_image(image, mask):
    return cv2.bitwise_and(image, image, mask=mask)


def segment_image(image, attempts = 10, k = 4, criteria = DEFAULT_SEG_CRT):
    td_img = np.float32(image.reshape((-1, 3)))
    _, label, center = cv2.kmeans(td_img, k, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)

    center = np.uint8(center)
    res = center[label.flatten()]

    return res.reshape((image.shape))


def detect_segmented_color_profile(image, lower_bound, upper_bound, blur_image = True):
    if blur_image is True:
        image = cv2.GaussianBlur(image, (5, 5), 0)
    image_masked = mask_image(image, MASK)
    segmented_image = segment_image(image_masked, k=6)
    color_mask = cv2.inRange(segmented_image, lower_bound, upper_bound)
    return cv2.bitwise_and(segmented_image, segmented_image, mask=color_mask)


def detect_plants(image, lower_adjust = -10, upper_adjust = 5):
    return detect_segmented_color_profile(
        image=image,
        lower_bound=np.array([90, 120, 40]) + lower_adjust,
        upper_bound=np.array([100, 220, 70]) + upper_adjust,
    )


def detect_ground(image, lower_adjust = -4, upper_adjust = 10):
    return detect_segmented_color_profile(
        image=image,
        lower_bound=np.array([105, 90, 55]) + lower_adjust,
        upper_bound=np.array([165, 140, 120]) + upper_adjust,
    )


def canny(image, thresh1 = 50, thresh2 = 100, blur_image = False):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    if blur_image is True:
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

    return cv2.Canny(gray, thresh1, thresh2)


def make_coordinates(image, line_params):
    slope, intercept = line_params

    y1 = image.shape[0]
    y2 = int(y1 * 0.6)
    x1 = int((y1 - intercept) / slope)
    x2 = int((y2 - intercept) / slope)
    return np.array([x1, y1, x2, y2])


def average_slope_intercep(image, lines):
    left_fit = []
    right_fit = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        params = np.polyfit((x1, x2), (y1, y2), 1)
        slope = params[0]
        intercept = params[1]
        if slope < 0:
            left_fit.append((slope, intercept))
        else:
            right_fit.append((slope, intercept))
    left_fit_average = np.average(left_fit, axis=0)
    right_fit_average = np.average(right_fit, axis=0)
    left_line = make_coordinates(image, left_fit_average)
    right_line = make_coordinates(image, right_fit_average)
    return np.array([left_line, right_line])

def hough_lines(image, min_line_len = 20, max_line_gap = 20):
    return cv2.HoughLinesP(image, 2, np.pi / 180, 10, np.array([]), min_line_len, max_line_gap)


def draw_lines_on_image(image, lines, color_rgb = (255, 0, 0)):
    line_image = np.zeros_like(image)

    if lines is not None:
        for x1, y1, x2, y2 in lines.reshape(-1, 4):
            cv2.line(line_image, (x1, y1), (x2, y2), color_rgb, 10)

    return cv2.addWeighted(image, 0.8, line_image, 1, 1)


def remove_dark_area(image, yy_thresh = 325):
    return image[0:yy_thresh, ::]