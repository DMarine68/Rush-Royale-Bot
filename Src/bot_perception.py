import os
import uuid

import numpy as np
import pandas as pd
import cv2
from sklearn.linear_model import LogisticRegression
import pickle


# internal

####
#### Unit type recognition
###

def get_image_keypoints_and_descriptors(image):
    size = 25
    orb = cv2.ORB.create(nfeatures=500,  # The maximum number of features to retain.
                         scaleFactor=1.2,  # Pyramid decimation ratio, greater than 1
                         nlevels=8,  # The number of pyramid levels.
                         edgeThreshold=size,
                         # This is size of the border where the features are not detected. It should roughly match the patchSize parameter
                         firstLevel=0,  # It should be 0 in the current implementation.
                         WTA_K=2,  # The number of points that produce each element of the oriented BRIEF descriptor.
                         scoreType=cv2.ORB_HARRIS_SCORE,
                         # The default HARRIS_SCORE means that Harris algorithm is used to rank features (the score is written to KeyPoint::score and is
                         # used to retain best nfeatures features); FAST_SCORE is alternative value of the parameter that produces slightly less stable
                         # keypoints, but it is a little faster to compute.
                         # scoreType = cv2.ORB_FAST_SCORE,
                         patchSize=size
                         )
    return orb.detectAndCompute(image, None)  # keypoints, descriptors


def get_unit_data():
    unit_data = {}
    files = os.listdir(os.path.join('all_units'))
    for file in files:
        if file == 'unit_rank':
            continue

        unit_name = file.replace('.png', '')

        path = os.path.join('all_units', file)
        img = cv2.imread(path)
        keypoints, descriptors = get_image_keypoints_and_descriptors(img)
        unit_data[unit_name] = {
            'keypoints': keypoints,
            'descriptors': descriptors
        }
    return unit_data


def orb_match_unit(img, ref_units, unit_data):
    keypoints, descriptors = get_image_keypoints_and_descriptors(img)
    best_unit_name = 'empty'
    best_unit_matches = 0
    best_unit_confidence = 0

    for unit_name, unit_info in unit_data.items():
        target_ref = False
        for ref_unit in ref_units:
            ru = ref_unit.replace('.png', '')
            if ru == unit_name:
                target_ref = True

        if not target_ref:
            continue

        train_keypoints = unit_info['keypoints']
        train_descriptors = unit_info['descriptors']

        if train_descriptors is None:
            continue

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        matches = bf.knnMatch(descriptors, train_descriptors, k=2)
        good_matches = []

        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        matches_mask = []
        if len(good_matches) > 4:
            src_pts = np.float32([keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([train_keypoints[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            matches_mask = mask.ravel().tolist()

            if len(matches_mask) > best_unit_matches:
                best_unit_matches = len(matches_mask)
                best_unit_name = unit_name
                best_unit_confidence = round(np.sum(mask) / mask.size, 3)

    # DO IT FOR SHARPSHOOTER_MAX TOO?!
    if best_unit_name == 'sharpshooter_active':
        best_unit_name = 'sharpshooter'
    elif best_unit_name == 'crystal_high_arcanist':
        best_unit_name = 'crystal'

    return [f'{best_unit_name}.png', best_unit_confidence]


# Get status of current grid
# Currently 0.082 seconds call, multithreading is about 0.64 seconds
def grid_status(ref_units, crop_img_data, unit_data, prev_grid=None):
    grid_stats = []
    debug = False
    x = 0
    for img_name, img_data in crop_img_data.items():
        if debug:
            cv2.imwrite(f'test{x}.png', img_data)
        x = x + 1

        rank, rank_prob = match_rank(img_data)
        unit_guess = orb_match_unit(img_data, ref_units, unit_data) if rank != 0 else ['empty.png', 0]

        # Curse does not work well for different ranks
        grid_stats.append([*unit_guess, rank, rank_prob])
    grid_df = pd.DataFrame(grid_stats, columns=['unit', 'u_prob', 'rank', 'r_prob'])
    # Add grid position
    box_id = [[(i // 5) % 5, i % 5] for i in range(15)]
    # grid_df.insert(0, 'grid_pos', box_id)
    grid_df['grid_pos'] = box_id
    if prev_grid is not None:
        # Check Consistency
        consistency = grid_df[['grid_pos', 'unit', 'rank']] == prev_grid[['grid_pos', 'unit', 'rank']]
        consistency = consistency.all(axis=1)
        # Update age from previous grid
        grid_df['Age'] = prev_grid['Age'] * consistency
        grid_df['Age'] += consistency
    else:
        grid_df['Age'] = np.zeros(len(grid_df))
    return grid_df


def match_rank(img):
    edges = cv2.Canny(img, 50, 100)

    with open('rank_model.pkl', 'rb') as f:
        logreg = pickle.load(f)
        classes = logreg.classes_
    prob = logreg.predict_proba(edges.reshape(1, -1))
    return prob.argmax(), round(prob.max(), 3)


# Fill find highest rank knight_statue adjacent to key_target
def position_filter(grid_df, key_target='demon_hunter.png'):
    demon_grid = grid_df[grid_df['unit'] == key_target]
    # Get max value index  in rank column
    demon_grid = demon_grid.sort_values(by='rank', ascending=False)
    unit_pos = demon_grid.iloc[0]['grid_pos']
    adjacent = unit_pos - np.array([[0, -1], [0, 1], [-1, 0], [1, 0]])
    # Keep only column values between 0 and 4 (bad rows are filtered out by isin)
    adjacent = adjacent[np.logical_and(adjacent[:, 1] >= 0, adjacent[:, 1] <= 4)]
    # Convert grid_pos to id 0-15 and extract rows
    adj_df = grid_df[grid_df.index.isin(adjacent[0:, 0] * 5 + adjacent[0:, 1])]
    adj_knights = adj_df[adj_df['unit'] == 'knight_statue.png'].sort_values(by='rank', ascending=True)
    key_pos = adj_knights.index[-1]
    return key_pos


## Add to dataset
def add_grid_to_dataset_orig():
    print('fix this')
    # for slot in os.listdir("OCR_inputs"):
    #     target = f'OCR_inputs/{slot}'
    #     img = cv2.imread(target, 0)
    #     edges = cv2.Canny(img, 50, 100)
    #     rank_guess = 0
    #     unit_guess = match_unit(target)
    #     if unit_guess[1] != 'empty.png':
    #         rank_guess, _ = match_rank(target)
    #     example_count = len(os.listdir("machine_learning/inputs"))
    #     cv2.imwrite(f'machine_learning/inputs/{rank_guess}_input_{example_count}.png', edges)
    #     cv2.imwrite(f'machine_learning/raw_input/{rank_guess}_raw_{example_count}.png', img)



# Add to dataset
def add_grid_to_dataset(selected_units):
    if not os.path.isdir('debug'):
        os.mkdir('debug')

    for img_name, img_data in selected_units.items():
        filename = f"{uuid.uuid4()}.png"
        cv2.imwrite(f'debug/{filename}', img_data)


def load_dataset(folder):
    x_train = []
    y_train = []
    for file in os.listdir(folder):
        if file.endswith(".png"):
            x_train.append(cv2.imread(folder + file, 0))
            y_train.append(file.split('_input')[0])
    x_train = np.array(x_train)
    data_shape = x_train.shape
    x_train = x_train.reshape(data_shape[0], data_shape[1] * data_shape[2])
    y_train = np.array(y_train, dtype=int)
    return x_train, y_train


def quick_train_model():
    x_train, y_train = load_dataset("machine_learning\\inputs\\")
    # train logistic regression model
    logreg = LogisticRegression()
    logreg.fit(x_train, y_train)
    return logreg
