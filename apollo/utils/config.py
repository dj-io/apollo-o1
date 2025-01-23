import os
import json
import questionary
from halo import Halo
import configparser

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "apollo")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_CONFIG = {"github_username": None, "cached_directories": [], "apollo_path": None}
spinner = Halo(spinner="dot")

def load_config():
    """Load configuration from the file or initialize default if it doesn't exist."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        spinner.info(f"Configuration file created at {CONFIG_FILE} with default values.")
    try:
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            
        # Merge the loaded config with the default config to include new keys
        updated_config = { **DEFAULT_CONFIG, **config }    
        
        # If the config was updated with new keys, save it back to the file
        if config != updated_config:
            save_config(updated_config)
            spinner.info("Configuration file updated with new default keys....")
            
        return updated_config
    
    except json.JSONDecodeError:
        raise ValueError(f"Configuration file at {CONFIG_FILE} is not a valid JSON file.")


def load_allowed_users():
    """Load configuration from the file or initialize default if it doesn't exist."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
            return config.get("allowed_users", [])
    return []

    
def save_config(config):
    """Save configuration to the file."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

def cache_username(config):
    # Cache GitHub username
    if not config["github_username"]:
        github_username = questionary.text("Enter your GitHub username:").ask()
        
        config["github_username"] = github_username.strip()
        save_config(config)
        spinner.info(f"GitHub username '{github_username}' saved for future use.")
    else:
        spinner.info(f"Using cached GitHub username: {config["github_username"]}")
        
    return config["github_username"]
        

def cache_apollo_path(config):
    # Cache apollo path
    if not config["apollo_path"]:
        APOLLO_PATH = os.getcwd()
        config["apollo_path"] = APOLLO_PATH 
        
        save_config(config)
        spinner.info(f"Apollo Path set as {APOLLO_PATH}")
    else:
        spinner.info(f"Using cached Path: '{config["apollo_path"]}'")
        
    return config["apollo_path"]


def ensure_pypirc(test):
    """
    Ensure the .pypirc file exists and has valid credentials for the selected repository.
    If credentials are invalid, prompt the user to provide valid values.
    """
    spinner = Halo(spinner="dots")
    pypirc_path = os.path.expanduser("~/.pypirc")
    repository = "testpypi" if test else "pypi"

    if not os.path.exists(pypirc_path):
        spinner.warn(".pypirc file not found.")
        
        create_pypirc = questionary.confirm(
            "The .pypirc file does not exist. Would you like to create one?"
        ).ask()
        
        if not create_pypirc:
            spinner.fail("Deployment aborted. .pypirc file is required for upload.")
            exit(1)
        
        # Gather credentials to create a new .pypirc file
        username = questionary.text(f"Enter your {repository} username (e.g., '__token__'):").ask()
        password = questionary.password(f"Enter your {repository} token:").ask()

        # Create and populate the .pypirc file
        spinner.start("Creating .pypirc file...")
        config = configparser.ConfigParser()
        config["distutils"] = {"index-servers": "pypi\ntestpypi"}
        config["pypi"] = {"repository": "https://upload.pypi.org/legacy/", "username": username, "password": password}
        config["testpypi"] = {"repository": "https://test.pypi.org/legacy/", "username": username, "password": password}
        
        with open(pypirc_path, "w") as configfile:
            config.write(configfile)
        spinner.succeed(".pypirc file created successfully.")
    else:
        # Validate the existing .pypirc file
        spinner.start(f"Validating .pypirc file for {repository}...")
        config = configparser.ConfigParser()
        config.read(pypirc_path)

        if repository not in config.sections():
            spinner.fail(f"The .pypirc file does not contain credentials for {repository}.")
            update_credentials = questionary.confirm("Would you like to add credentials now?").ask()
            if update_credentials:
                username = questionary.text(f"Enter your {repository} username (e.g., '__token__'):").ask()
                password = questionary.password(f"Enter your {repository} token:").ask()
                
                config[repository] = {"repository": f"https://{repository}.pypi.org/legacy/", "username": username, "password": password}
                
                with open(pypirc_path, "w") as configfile:
                    config.write(configfile)
                spinner.succeed(f"Added credentials for {repository}.")
            else:
                spinner.fail("Deployment aborted.")
                exit(1)
        
        username = config[repository].get("username")
        password = config[repository].get("password")
        
        if not username or username != "__token__":
            spinner.warn(f"Invalid username in .pypirc for {repository}.")
            username = questionary.text(f"Enter your {repository} username (e.g., '__token__'):").ask()
            
            config[repository]["username"] = username
        
        if not password or password.lower() == "none":
            spinner.warn(f"Invalid or missing token in .pypirc for {repository}.")
            password = questionary.password(f"Enter your {repository} token:").ask()
            
            config[repository]["password"] = password

        with open(pypirc_path, "w") as configfile:
            config.write(configfile)
        
        spinner.succeed(f".pypirc file is valid for {repository}.")

    return True