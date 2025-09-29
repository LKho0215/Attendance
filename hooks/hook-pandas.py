
# PyInstaller hook for pandas
from PyInstaller.utils.hooks import collect_all, collect_submodules

# Collect all pandas submodules
hiddenimports = collect_submodules('pandas')

# Additional pandas submodules that might be missed
hiddenimports += [
    'pandas._libs.tslibs.base',
    'pandas._libs.tslibs.timestamps',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.offsets',
    'pandas._libs.window.aggregations',
    'pandas.core.dtypes.common',
    'pandas.core.dtypes.generic',
    'pandas.core.dtypes.inference',
    'pandas.core.dtypes.missing',
    'pandas.io.formats.format',
    'pandas.io.formats.printing',
    'pandas.plotting._core',
    'pandas.core.arrays.boolean',
    'pandas.core.arrays.integer',
    'pandas.core.arrays.string_',
    'pandas.core.arrays.categorical',
    'pandas.core.arrays.period',
    'pandas.core.arrays.datetimes',
    'pandas.core.arrays.timedeltas',
]

# Collect data files and binaries
datas, binaries, hiddenimports_tmp = collect_all('pandas')
hiddenimports += hiddenimports_tmp
