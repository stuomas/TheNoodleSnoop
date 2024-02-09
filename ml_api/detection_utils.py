#!/usr/bin/env python

import cv2
import numpy as np
import requests
import io
import time
import base64
import json

from PIL import Image, ImageDraw
from os import path, environ
from object_detection.detection_model import load_net, detect

THRESH = float(environ.get('THRESH'))
THRESHOLD_LOW = float(environ.get('THRESHOLD_LOW'))
THRESHOLD_HIGH = float(environ.get('THRESHOLD_HIGH'))
INIT_SAFE_FRAME_NUM = int(environ.get('INIT_SAFE_FRAME_NUM'))
EWM_ALPHA = float(environ.get('EWM_ALPHA'))
ROLLING_WIN_SHORT = int(environ.get('ROLLING_WIN_SHORT'))
ROLLING_WIN_LONG = int(environ.get('ROLLING_WIN_LONG'))
ROLLING_MEAN_SHORT_MULTIPLE = float(environ.get('ROLLING_MEAN_SHORT_MULTIPLE'))
DETECTIVE_SENSITIVITY = float(environ.get('DETECTIVE_SENSITIVITY'))
VISUALIZATION_THRESH = float(environ.get('VISUALIZATION_THRESHOLD'))
SNAPSHOT_URL = environ.get('SNAPSHOT_URL', '')
STREAM_URL = environ.get('STREAM_URL', '')

model_dir = path.join(path.dirname(path.realpath(__file__)), 'model')
net_main = load_net(path.join(model_dir, 'model.cfg'), path.join(model_dir, 'model.meta'))

prediction = {
    'current_confidence_sum': 0,
    'current_frame_num': 0,
    'lifetime_frame_num': 0,
    'ewm_mean': 0,
    'rolling_mean_short': 0,
    'rolling_mean_long': 0
}


def get_detections():
    if SNAPSHOT_URL != '':
        img_data = requests.get(SNAPSHOT_URL, stream=True).content
        img_array = np.array(bytearray(img_data), dtype=np.uint8)
        img = cv2.imdecode(img_array, -1)
    elif STREAM_URL != '':
        cap = cv2.VideoCapture(STREAM_URL)
        _, img = cap.read()
        img_data = cv2.imencode('.jpg', img)[1].tobytes()
    else:
        raise ValueError('Missing configuration: SNAPSHOT_URL or STREAM_URL required')

    detections = detect(net_main, img, thresh=THRESH)
    detections_to_visualize = [d for d in detections if d[1] > VISUALIZATION_THRESH]
    overlay_detections(Image.open(io.BytesIO(img_data)), detections_to_visualize)

    global prediction
    current_confidence_sum = sum_p_in_detections(detections)
    prediction['current_confidence_sum'] = current_confidence_sum
    prediction['current_frame_num'] += 1
    prediction['lifetime_frame_num'] += 1
    prediction['ewm_mean'] = next_ewm_mean(current_confidence_sum, prediction['ewm_mean'])
    prediction['rolling_mean_short'] = next_rolling_mean(current_confidence_sum, prediction['rolling_mean_short'], prediction['current_frame_num'], ROLLING_WIN_SHORT)
    prediction['rolling_mean_long'] = next_rolling_mean(current_confidence_sum, prediction['rolling_mean_long'], prediction['lifetime_frame_num'], ROLLING_WIN_LONG)

    return {
        'failing': is_failing(prediction),
        'raw_detections': detections,
        'raw_predictions':  prediction,
        'overlay': base64.b64encode(img_data).decode(),
        'timestamp': time.time()
    }


def overlay_detections(img, detections):
    draw = ImageDraw.Draw(img)
    for d in detections:
        (xc, yc, w, h) = map(int, d[2])
        (x1, y1), (x2, y2) = (xc - w // 2, yc - h // 2), (xc + w // 2, yc + w // 2)
        points = (x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)
        draw.line(points, fill=(0, 255, 0, 255), width=3)
    return img


def is_failing(pred):
    if pred['current_frame_num'] < INIT_SAFE_FRAME_NUM:
        return False

    adjusted_ewm_mean = (pred['ewm_mean'] - pred['rolling_mean_long']) * DETECTIVE_SENSITIVITY
    if adjusted_ewm_mean < THRESHOLD_LOW:
        return False

    if adjusted_ewm_mean > THRESHOLD_HIGH:
        return True

    if adjusted_ewm_mean > (pred['rolling_mean_short'] - pred['rolling_mean_long']) * ROLLING_MEAN_SHORT_MULTIPLE:
        return True


def next_ewm_mean(p, current_ewm_mean):
    return p * EWM_ALPHA + current_ewm_mean * (1-EWM_ALPHA)


def next_rolling_mean(p, current_rolling_mean, count, win_size):
    return current_rolling_mean + (p - current_rolling_mean)/float(win_size if win_size <= count else count+1)


def sum_p_in_detections(detections):
    return sum([d[1] for d in detections])
