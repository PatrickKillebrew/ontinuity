"""
CAMERA CTE - Perception Layer
==============================
Computes Cross Track Error from raw camera image.
Replaces simulator's native CTE gift.

Architecture:
- Layer 1: Yellow line tracking (primary)
- Layer 2: Road surface segmentation (fallback + corridor definition)

Returns normalized CTE: -1.0 (far left) to +1.0 (far right)
Negative = car is right of center (needs to steer left)
Positive = car is left of center (needs to steer right)

Tuning parameters are in CONFIGURATION section.
All values were set from visual inspection of simulator camera images.
Retune if deploying on real hardware.
"""

import cv2
import numpy as np


# -----------------------------------------
# CONFIGURATION — tune these if needed
# -----------------------------------------

# Image crop — only look at bottom portion of frame
# Road is always in bottom half, sky/scenery always above
CROP_TOP_FRACTION   = 0.45   # ignore top 45% of image (sky, horizon)
CROP_BOTTOM_FRACTION = 0.95  # ignore bottom 5% (car hood may appear)

# Yellow line HSV thresholds
# H: 15-35 covers yellow-orange range
# S: >80 ensures saturated yellow not washed out white
# V: >80 ensures bright enough to be road marking
YELLOW_H_LOW  = 15
YELLOW_H_HIGH = 35
YELLOW_S_LOW  = 80
YELLOW_V_LOW  = 80

# Minimum yellow pixels to trust Layer 1 detection
YELLOW_MIN_PIXELS = 50

# Road surface sampling — sample from this region to get road color
# Center bottom of image — car is always on road here
ROAD_SAMPLE_X = (0.35, 0.65)   # horizontal: 35%-65% of width
ROAD_SAMPLE_Y = (0.80, 0.95)   # vertical: 80%-95% of height

# Road surface color tolerance in HSV
ROAD_HUE_TOLERANCE = 25
ROAD_SAT_TOLERANCE = 40
ROAD_VAL_TOLERANCE = 60

# Confidence threshold — below this, use Layer 2
LAYER1_CONFIDENCE_THRESHOLD = 0.3

# Output smoothing — prevents steering jerk on noisy frames
SMOOTHING_ALPHA = 0.7   # higher = more smoothing, more lag


# -----------------------------------------
# STATE
# -----------------------------------------

_prev_cte       = 0.0
_prev_confidence = 0.0


# -----------------------------------------
# LAYER 1: YELLOW LINE TRACKING
# -----------------------------------------

def _detect_yellow_line(crop):
    """
    Find yellow line pixels in cropped image.
    Returns (centroid_x, confidence) where:
        centroid_x is 0.0-1.0 normalized horizontal position
        confidence is 0.0-1.0
    """
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    lower = np.array([YELLOW_H_LOW,  YELLOW_S_LOW, YELLOW_V_LOW])
    upper = np.array([YELLOW_H_HIGH, 255,          255         ])
    mask  = cv2.inRange(hsv, lower, upper)

    pixel_count = np.sum(mask > 0)
    h, w        = crop.shape[:2]

    if pixel_count < YELLOW_MIN_PIXELS:
        return 0.5, 0.0   # center, zero confidence

    # Find centroid of yellow pixels
    moments = cv2.moments(mask)
    if moments["m00"] == 0:
        return 0.5, 0.0

    cx         = moments["m10"] / moments["m00"]
    centroid_x = cx / w   # normalize to 0.0-1.0

    # Confidence based on pixel count — more pixels = more confident
    max_expected = h * w * 0.15   # yellow shouldn't be more than 15% of frame
    confidence   = min(1.0, pixel_count / max_expected)

    return centroid_x, confidence


# -----------------------------------------
# LAYER 2: ROAD SURFACE SEGMENTATION
# -----------------------------------------

def _sample_road_color(img_hsv, h, w):
    """
    Sample the road surface color from the center-bottom region.
    Returns mean HSV values of road surface.
    """
    y1 = int(h * ROAD_SAMPLE_Y[0])
    y2 = int(h * ROAD_SAMPLE_Y[1])
    x1 = int(w * ROAD_SAMPLE_X[0])
    x2 = int(w * ROAD_SAMPLE_X[1])

    sample = img_hsv[y1:y2, x1:x2]
    mean   = np.median(sample.reshape(-1, 3), axis=0)
    return mean


def _detect_road_boundaries(crop):
    """
    Find left and right road boundaries using adaptive surface segmentation.
    Returns (left_x, right_x, confidence) normalized 0.0-1.0.
    """
    h, w   = crop.shape[:2]
    hsv    = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    road_color = _sample_road_color(hsv, h, w)

    # Create road mask — pixels similar to sampled road color
    lower = np.array([
        max(0,   road_color[0] - ROAD_HUE_TOLERANCE),
        max(0,   road_color[1] - ROAD_SAT_TOLERANCE),
        max(0,   road_color[2] - ROAD_VAL_TOLERANCE)
    ])
    upper = np.array([
        min(180, road_color[0] + ROAD_HUE_TOLERANCE),
        min(255, road_color[1] + ROAD_SAT_TOLERANCE),
        min(255, road_color[2] + ROAD_VAL_TOLERANCE)
    ])
    road_mask = cv2.inRange(hsv, lower, upper)

    # Morphological cleanup — remove noise
    kernel    = np.ones((3, 3), np.uint8)
    road_mask = cv2.morphologyEx(road_mask, cv2.MORPH_CLOSE, kernel)
    road_mask = cv2.morphologyEx(road_mask, cv2.MORPH_OPEN,  kernel)

    # Find road boundaries by scanning bottom third horizontally
    scan_row  = int(h * 0.85)
    row       = road_mask[scan_row, :]

    road_pixels = np.where(row > 0)[0]

    if len(road_pixels) < 10:
        return 0.0, 1.0, 0.0   # full width, zero confidence

    left_x  = road_pixels[0]  / w
    right_x = road_pixels[-1] / w

    # Confidence based on how much road is visible
    road_width  = right_x - left_x
    confidence  = min(1.0, road_width / 0.6)   # expect at least 60% road width

    return left_x, right_x, confidence


# -----------------------------------------
# MAIN FUNCTION
# -----------------------------------------

def compute_camera_cte(obs, debug=False):
    """
    Compute CTE from raw camera observation.

    Args:
        obs:   numpy array (120, 160, 3) RGB from gym env
        debug: if True, returns debug dict with internals

    Returns:
        float: CTE in range -1.0 to +1.0
               negative = car is right of center (steer left)
               positive = car is left of center  (steer right)
        If debug=True, returns (cte, debug_dict)
    """
    global _prev_cte, _prev_confidence

    # Convert RGB to BGR for OpenCV
    img = cv2.cvtColor(obs, cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]

    # Crop to road region
    y1   = int(h * CROP_TOP_FRACTION)
    y2   = int(h * CROP_BOTTOM_FRACTION)
    crop = img[y1:y2, :]

    # ── LAYER 1: Yellow line ──────────────────────────────────
    yellow_x, yellow_conf = _detect_yellow_line(crop)

    layer_used = "L1"

    if yellow_conf >= LAYER1_CONFIDENCE_THRESHOLD:
        # Yellow line found — CTE is offset from center
        # yellow_x is 0.0-1.0; 0.5 = centered
        # Positive CTE = yellow line is left of center = car is left of center
        raw_cte = (yellow_x - 0.5) * 2.0   # scale to -1.0 to +1.0

    else:
        # ── LAYER 2: Road surface ─────────────────────────────
        layer_used = "L2"
        left_x, right_x, road_conf = _detect_road_boundaries(crop)

        if road_conf < 0.1:
            # Neither layer confident — hold last known CTE
            layer_used = "HOLD"
            raw_cte    = _prev_cte
        else:
            corridor_center = (left_x + right_x) / 2.0
            raw_cte         = (corridor_center - 0.5) * 2.0

    # Clip to valid range
    raw_cte = max(-1.0, min(1.0, raw_cte))

    # Smooth output to prevent steering jerk
    cte = SMOOTHING_ALPHA * _prev_cte + (1.0 - SMOOTHING_ALPHA) * raw_cte

    _prev_cte        = cte
    _prev_confidence = yellow_conf

    if debug:
        return cte, {
            "layer":       layer_used,
            "yellow_x":    yellow_x,
            "yellow_conf": yellow_conf,
            "raw_cte":     raw_cte,
            "smoothed_cte": cte,
        }

    return cte


# -----------------------------------------
# STANDALONE TEST
# Run: python camera_cte.py path/to/image.png
# -----------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python camera_cte.py <image_path>")
        sys.exit(1)

    img_path = sys.argv[1]
    img_bgr  = cv2.imread(img_path)

    if img_bgr is None:
        print(f"Could not load image: {img_path}")
        sys.exit(1)

    # Convert BGR to RGB as the gym env would provide
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    cte, dbg = compute_camera_cte(img_rgb, debug=True)

    print(f"Camera CTE: {cte:.4f}")
    print(f"  Layer used:   {dbg['layer']}")
    print(f"  Yellow pos:   {dbg['yellow_x']:.3f} (conf: {dbg['yellow_conf']:.3f})")
    print(f"  Raw CTE:      {dbg['raw_cte']:.4f}")
    print(f"  Smoothed CTE: {dbg['smoothed_cte']:.4f}")

    # Save debug visualization
    img_h, img_w = img_bgr.shape[:2]
    y1 = int(img_h * CROP_TOP_FRACTION)
    y2 = int(img_h * CROP_BOTTOM_FRACTION)
    crop = img_bgr[y1:y2, :]

    # Draw crop region
    debug_img = img_bgr.copy()
    cv2.rectangle(debug_img, (0, y1), (img_w, y2), (0, 255, 0), 1)

    # Draw yellow mask
    hsv  = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,
        np.array([YELLOW_H_LOW,  YELLOW_S_LOW, YELLOW_V_LOW]),
        np.array([YELLOW_H_HIGH, 255,          255          ]))
    mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    mask_colored[:,:,0] = 0   # remove blue
    mask_colored[:,:,1] = 0   # remove green — show red only

    # Draw CTE line
    center_x = int(img_w * 0.5)
    cte_x    = int(img_w * (0.5 - cte * 0.5))
    cv2.line(debug_img, (center_x, y2), (center_x, y1), (255, 255, 255), 1)
    cv2.line(debug_img, (cte_x,    y2), (cte_x,    y1), (0,   255, 0  ), 2)

    out_path = img_path.replace(".png", "_debug.png").replace(".jpg", "_debug.jpg")
    cv2.imwrite(out_path, debug_img)
    print(f"Debug image saved: {out_path}")
