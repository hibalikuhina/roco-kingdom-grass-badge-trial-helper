"""Tunable constants for the icon matcher."""

# --- normalisation -----------------------------------------------------
NORM_SIZE = 128          # normalised icon is NORM_SIZE x NORM_SIZE RGBA
BG_TOL = 30              # per-channel distance from background colour that
                         # still counts as background (bg has light texture)
FRAME_FACTOR = 1.45      # crop side, as a multiple of the icon equivalent
                         # diameter (see imaging.Blob)
MARGIN = 0.10            # extra padding on top of that, as a fraction
CANON_BG = (236, 230, 214)   # every normalised icon gets this background
DESC_BLUR = 1.6          # blur applied to both sides before describing, so a
                         # 60px screenshot and a 220px one compare fairly

# --- descriptor weights (must sum to 1.0) ------------------------------
# (tuned on tests/test_pipeline.py, which is deliberately harsher than real
#  icons: every synthetic icon there shares the same frame, eyes and mouth)
W_GRID = 0.30            # coarse colour layout
W_HIST = 0.35            # colour histogram over the icon pixels only
W_HASH = 0.15            # perceptual (DCT) hash of the greyscale icon
W_SHAPE = 0.20           # silhouette

# --- decision thresholds (overridable per DB in its index.json) --------
# The verdict uses two numbers.  "similarity" is the raw descriptor score of
# the best candidate; "stand-out" is how far that candidate rises above the
# median of the rest of the database.  Similarity alone is not enough: every
# icon of this game shares a black disc on the same background, so the whole
# similarity scale slides upwards as the database grows.  Stand-out is scale
# free and keeps one operating point from 14 icons to 250 (see tests/).
MATCH_SIM = 0.80         # both must hold for a "Y"
MATCH_REL = 0.70
DUP_SIM = 0.78           # both must hold to warn before adding; deliberately
DUP_REL = 0.55           # looser than the match rule - over-warning is cheap,
                         # a duplicate icon in the database is not
MIN_ICONS_FOR_REL = 4    # below this the median is meaningless -> similarity only

DESCRIPTOR_VERSION = 1
