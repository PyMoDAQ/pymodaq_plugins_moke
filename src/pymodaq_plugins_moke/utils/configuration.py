from pathlib import Path
from pymodaq.daq_utils.config import Config, load_config, get_set_local_dir

config_base_path = Path(__file__).parent.parent.joinpath('config_moke_template.toml')
config_path = get_set_local_dir().joinpath('config_moke.toml')


class Config(Config):
    def __init__(self):
        super().__init__(config_path, config_base_path)

