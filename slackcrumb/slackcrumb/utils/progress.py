"""Progress bar wrapper using tqdm."""

from tqdm import tqdm


def progress_bar(iterable=None, total=None, desc="", unit="msg", **kwargs):
    """Create a tqdm progress bar with consistent styling."""
    return tqdm(
        iterable,
        total=total,
        desc=desc,
        unit=unit,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        **kwargs,
    )
