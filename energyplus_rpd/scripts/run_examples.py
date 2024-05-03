from energyplus_rpd.runner import run_with_path
from pathlib import Path


def run_example_files():
    print('before run of example files')
    try:
        run_with_path(Path('../example/ASHRAE901_OfficeSmall_STD2019_Denver.epJSON'))
    except Exception as e:
        print(f"Could not process example file; error: {e}")
        raise
    print('finished running example files')


if __name__ == "__main__":
    exit(run_example_files())
