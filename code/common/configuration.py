from pathlib import Path

import common.utilities as utilities


class Configuration:
    CONFIG_NAME = "config.json"	            # The name of the config file
    PROD_CONFIG_NAME = "config.prod.json"   # The name of the prod config file
    DEV_CONFIG_NAME = "config.dev.json"     # The name of the dev config file


    @staticmethod
    def _load_config_chunks(directory_path: Path = None) -> dict:
        '''
        Loads configuration data from the given directory (or the app's root if not provided) into a dictionary. The
        expected prod, dev, and config configuration files are loaded separately and combined into the same dict under
        different keys ("dev", "prod", "config").

        :param directory_path: Optional path to load configuration files from. If None, then the program's root (cwd/..) will be searched.
        :type directory_path: Path, optional
        :return: Dictionary containing individual dev, prod, and root config items.
        :rtype: dict
        '''

        path = directory_path or utilities.get_root_path()
        config = {}

        dev_config_path = Path.joinpath(path, Configuration.DEV_CONFIG_NAME)
        if (dev_config_path.exists()):
            config["dev"] =  utilities.load_json(dev_config_path)

        prod_config_path = Path.joinpath(path, Configuration.PROD_CONFIG_NAME)
        if (prod_config_path.exists()):
            config["prod"] = utilities.load_json(prod_config_path)

        config_path = Path.joinpath(path, Configuration.CONFIG_NAME)
        if (config_path.exists()):
            config["config"] = utilities.load_json(config_path)

        return config


    @staticmethod
    def load_config(directory_path: Path = None) -> dict:
        '''
        Parses one or more JSON configuration files to build a dictionary with proper precedence for configuring the program

        :param directory_path: Optional path to load configuration files from. If None, then the program's root (cwd/..) will be searched.
        :type directory_path: Path, optional
        :return: A dictionary containing key-value pairs for use in configuring parts of the program.
        :rtype: dict
        '''

        root_config_chunks = Configuration._load_config_chunks(utilities.get_root_path())

        config_chunks = {}
        if (directory_path is not None):
            config_chunks = Configuration._load_config_chunks(directory_path)

        ## Build up a configuration hierarchy, allowing for global configuration if desired
        ## See: https://github.com/naschorr/hawking/issues/181
        config  = root_config_chunks.get("config", {})
        config |= config_chunks.get("config", {})
        config |= root_config_chunks.get("prod", {})
        config |= root_config_chunks.get("dev", {})
        config |= config_chunks.get("prod", {})
        config |= config_chunks.get("dev", {})

        return config
