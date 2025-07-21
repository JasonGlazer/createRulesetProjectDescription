from energyplus_rpd.runner import run_with_path
from pathlib import Path


def generate_rpd_for_all_229_models():
    """
    Generate RPD files for FSEC and PSD's EnergyPlus models of the 229P test suite.
    """
    # Path to the directory containing the 229P models
    base_dir = Path(__file__).parent

    fsec_models_dir = base_dir / "test_files_229_FSEC"
    psd_models_dir = base_dir / "test_files_229_PSD"

    print(f"Processing models in directory: {fsec_models_dir}")
    # Iterate through each model file in the directory
    for model_file in fsec_models_dir.rglob('*.epJSON'):
        print(f'Processing {model_file.name}...')
        run_with_path(model_file)  # Call the function to process the model file
        print(f'Finished processing {model_file.name}.')

    print(f"Processing models in directory: {psd_models_dir}")
    # Iterate through each model file in the directory
    for model_file in psd_models_dir.rglob('*.epJSON'):
        print(f'Processing {model_file.name}...')
        run_with_path(model_file)  # Call the function to process the model file
        print(f'Finished processing {model_file.name}.')


if __name__ == "__main__":
    generate_rpd_for_all_229_models()
    print("All models processed successfully.")