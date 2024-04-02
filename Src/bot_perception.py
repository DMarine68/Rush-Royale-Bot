import os
import numpy as np
import pandas as pd
import cv2
from sklearn.linear_model import LogisticRegression
import pickle


# internal

####
#### Unit type recognition
###

def get_image_keypoints_and_descriptors(path):
    image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
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
        keypoints, descriptors = get_image_keypoints_and_descriptors(path)
        unit_data[unit_name] = {
            'keypoints': keypoints,
            'descriptors': descriptors
        }
    return unit_data


# Get most common pixel RGB value in image
def get_color(filename, crop=False):
    unit_img = cv2.imread(filename)
    if crop:
        unit_img = unit_img[15:15 + 90, 17:17 + 90]
    unit_img = cv2.cvtColor(unit_img, cv2.COLOR_BGR2RGB)
    # Flatten to pixel values
    flat_img = unit_img.reshape(-1, unit_img.shape[2])
    flat_img_round = flat_img // 20 * 20
    unique, counts = np.unique(flat_img_round, axis=0, return_counts=True)
    colors = np.zeros((5, 3), dtype=int)
    if len(unique) < 10:
        return colors
    # Sort list
    sorted_count = np.sort(counts)[::-1]
    # Get index of the most common colors
    for i in range(0, 5):
        index = np.where(counts == sorted_count[i])[0][0]
        colors[i] = unique[index]
    return colors


# Match unit based on color
def match_unit(filename, ref_colors, ref_units):
    unit_colors = get_color(filename, crop=True)
    # Find closest match (mean squared error)
    for color in unit_colors:
        mse = np.sum((ref_colors - color) ** 2, axis=1)
        # Dryad sometimes needs 2000 to match
        if mse[mse.argmin()] <= 2000:
            return ref_units[mse.argmin()], round(mse[mse.argmin()])
    return ['empty.png', 2001]


def orb_match_unit(filename, ref_units, unit_data):
    keypoints, descriptors = get_image_keypoints_and_descriptors(filename)
    best_unit_name = 'empty'
    best_unit_matches = 0

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

    # DO IT FOR SHARPSHOOTER_MAX TOO?!
    if best_unit_name == 'sharpshooter_active':
        best_unit_name = 'sharpshooter'
    elif best_unit_name == 'crystal_high_arcanist':
        best_unit_name = 'crystal'

    return [f'{best_unit_name}.png', 2001]



# Get status of current grid
# Currently 0.082 seconds call, multithreading is about 0.64 seconds
def grid_status(names, unit_data, prev_grid=None):
    ref_units = os.listdir('units')
    # ref_colors = [get_color('units/' + unit)[0] for unit in ref_units]
    grid_stats = []
    for filename in names:
        rank, rank_prob = match_rank(filename)
        # unit_guess = match_unit(filename, ref_colors, ref_units) if rank != 0 else ['empty.png', 0]
        unit_guess = orb_match_unit(filename, ref_units, unit_data) if rank != 0 else ['empty.png', 0]

        # Curse does not work well for different ranks
        # unit_guess = unit_guess if not is_cursed(filename) else ['cursed.png',0]
        grid_stats.append([*unit_guess, rank, rank_prob])
    grid_df = pd.DataFrame(grid_stats, columns=['unit', 'u_prob', 'rank', 'r_prob'])
    # Add grid position
    box_id = [[(i // 5) % 5, i % 5] for i in range(15)]
    grid_df.insert(0, 'grid_pos', box_id)
    if not prev_grid is None:
        # Check Consistency
        consistency = grid_df[['grid_pos', 'unit', 'rank']] == prev_grid[['grid_pos', 'unit', 'rank']]
        consistency = consistency.all(axis=1)
        # Update age from previous grid
        grid_df['Age'] = prev_grid['Age'] * consistency
        grid_df['Age'] += consistency
    else:
        grid_df['Age'] = np.zeros(len(grid_df))
    return grid_df


def match_rank(filename):
    img = cv2.imread(filename, 0)
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
def add_grid_to_dataset():
    for slot in os.listdir("OCR_inputs"):
        target = f'OCR_inputs/{slot}'
        img = cv2.imread(target, 0)
        edges = cv2.Canny(img, 50, 100)
        rank_guess = 0
        unit_guess = match_unit(target)
        if unit_guess[1] != 'empty.png':
            rank_guess, _ = match_rank(target)
        example_count = len(os.listdir("machine_learning/inputs"))
        cv2.imwrite(f'machine_learning/inputs/{rank_guess}_input_{example_count}.png', edges)
        cv2.imwrite(f'machine_learning/raw_input/{rank_guess}_raw_{example_count}.png', img)


def load_dataset(folder):
    X_train = []
    Y_train = []
    for file in os.listdir(folder):
        if file.endswith(".png"):
            X_train.append(cv2.imread(folder + file, 0))
            Y_train.append(file.split('_input')[0])
    X_train = np.array(X_train)
    data_shape = X_train.shape
    X_train = X_train.reshape(data_shape[0], data_shape[1] * data_shape[2])
    Y_train = np.array(Y_train, dtype=int)
    return X_train, Y_train


def quick_train_model():
    X_train, Y_train = load_dataset("machine_learning\\inputs\\")
    # train logistic regression model
    logreg = LogisticRegression()
    logreg.fit(X_train, Y_train)
    return logreg
