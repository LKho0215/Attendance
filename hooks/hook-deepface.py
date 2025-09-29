
# PyInstaller hook for DeepFace
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all deepface submodules
hiddenimports = collect_submodules('deepface')

# Additional deepface modules
hiddenimports += [
    'deepface.models.ArcFace',
    'deepface.commons.functions',
    'deepface.commons.distance',
    'deepface.detectors.OpenCv',
    'deepface.detectors.FaceDetector',
    'deepface.detectors.DetectorWrapper',
]

# Collect data files and binaries
datas, binaries, hiddenimports_tmp = collect_all('deepface')
hiddenimports += hiddenimports_tmp
