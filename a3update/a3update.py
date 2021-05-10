import click
import os
import yaml
import shutil
from pysteamcmdwrapper import SteamCMD, SteamCMDException
from steam.webapi import WebAPI

ARMA_APPID = 107410


# noinspection PyGlobalUndefined
@click.command()
@click.option('--validate/--no-validate', default=True, help='Validate apps and workshop items')
@click.option('-u', '--username', prompt='Steam username', default='anonymous', show_default=True,
              help='Username used for Steam')
@click.option('-p', '--password', prompt='Steam password', default='', show_default=True,
              hide_input=True, help='Password used for Steam')
@click.option('-c', '--config', type=click.Path(readable=True, resolve_path=True),
              default='a3update.yaml', help='Path to a3update.yaml')
@click.option('-n', '--no-update', is_flag=True, default=False, help='Skips updating mods and Arma')
@click.option('-s', '---setup', is_flag=True, default=False, help='Runs initial setup')
def cli(validate, username, password, config, no_update, _setup):
    # Check yaml existence
    if _setup:
        setup(config)
    elif not os.path.isfile(config):
        if click.confirm('No configuration file detected, do you wish to create a new one'):
            setup(config)
        else:
            config = click.prompt('Enter path to a3update.yaml',
                                  type=click.Path(exists=True, readable=True, resolve_path=True))

    with open(config, 'r') as file:
        global CONFIG_YAML
        CONFIG_YAML = yaml.safe_load(file)

    # Login to SteamCMD and WebAPI
    click.echo("Checking SteamCMD install")
    global STEAM_CMD
    STEAM_CMD = SteamCMD(CONFIG_YAML['steamcmd_dir'])
    try:
        STEAM_CMD.install()
    except SteamCMDException:
        click.echo("SteamCMD installed")
    STEAM_CMD.login(username, password)
    global STEAM_WEBAPI
    STEAM_WEBAPI = WebAPI(key=CONFIG_YAML['api_key'])

    # Load constants
    global WORKSHOP_DIR
    WORKSHOP_DIR = CONFIG_YAML['mod_dir_full']
    global INSTALL_DIR
    INSTALL_DIR = CONFIG_YAML['install_dir']
    global KEY_PATH
    KEY_PATH = os.path.join(INSTALL_DIR, 'keys')

    # Update apps (Arma 3 Dedicated Server, CDLCs)
    click.echo('Updating Apps')
    appids = [CONFIG_YAML['server_appid']] + CONFIG_YAML['cdlc']
    for appid in appids:
        if not no_update:
            STEAM_CMD.app_update(appid, INSTALL_DIR, validate)

    # Update mods
    click.echo('Updating mods')
    if CONFIG_YAML['handle_keys']:
        # Delete key symlinks
        for filename in os.listdir(KEY_PATH):
            f = os.path.join(INSTALL_DIR, filename)
            if os.path.islink(f):
                os.unlink(f)

    mods = workshop_ids_to_mod_array(get_collection_workshop_ids(CONFIG_YAML['collections']))
    for mod in mods:
        click.echo('Updating {}'.format(mod['name']))

        # Create symbolic links to keep files lowercase without renaming
        if not no_update:
            STEAM_CMD.workshop_update(ARMA_APPID, mod['published_file_id'], CONFIG_YAML['mod_dir'], validate)
        path = os.path.join(WORKSHOP_DIR, mod['published_file_id'])
        create_mod_link(
            path,
            os.path.join(INSTALL_DIR, mod['folder_name'])
        )

        if CONFIG_YAML['handle_keys']:
            # Create key symlinks
            if not create_key_links(path):
                click.echo('WARN: No bikeys found for: {}'.format(mod['name']))

    if CONFIG_YAML['a3sync']['active']:
        from a3update import arma3sync
        click.echo('Updating ArmA3Sync Repo')
        arma3sync.update(mods, CONFIG_YAML)

    if CONFIG_YAML['html_preset']['active']:
        from a3update import html_preset
        click.echo('Generating Arma Launcher Preset')
        html_preset.generate(mods, CONFIG_YAML)

    if CONFIG_YAML['swifty']['active']:
        from a3update import swifty
        click.echo('Updating Swifty Repo')
        swifty.update(mods, CONFIG_YAML)

    click.echo('Finished!')


def create_key_links(path):
    keys = find_bikeys(path)
    linked_keys = []
    if keys:
        for key in keys:
            key_link = os.path.basename(key).lower()
            key_path = os.path.join(KEY_PATH, key_link)
            if not os.path.exists(key_path):
                os.symlink(
                    key,
                    key_path
                )
                linked_keys.append(key_link)
            else:
                click.echo('WARN: Duplicate key: {}'.format(key_link))

    return linked_keys


def find_bikeys(path):
    keys = []

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.lower().endswith('.bikey'):
                keys.append(os.path.join(root, file))
    return keys


def create_mod_link(input_path, output_path):
    if os.path.isdir(output_path):
        shutil.rmtree(output_path)

    os.mkdir(output_path)

    for filename in os.listdir(input_path):
        f = os.path.join(input_path, filename)
        if os.path.isdir(f):
            create_mod_link(f, os.path.join(output_path, filename.lower()))
        else:
            os.symlink(f, os.path.join(output_path, filename.lower()))


def workshop_ids_to_mod_array(workshop_ids):
    published_file_details = get_published_file_details(workshop_ids)

    mod_arr = []
    for i in range(0, published_file_details['resultcount']):
        file_details = published_file_details['publishedfiledetails'][i]

        mod_arr.append({
            'name': file_details['title'],
            'folder_name': '@{}'.format(file_details['title'].lower().replace(' ', '_')),
            'published_file_id': file_details['publishedfileid'],
        })

    return mod_arr


def get_collection_workshop_ids(collection_ids, nested_collections=True):
    workshop_items = []
    collection_details = get_collection_details(collection_ids)

    for i in range(0, collection_details['resultcount']):
        collection = collection_details['collectiondetails'][i]
        click.echo('Processing collection {}'.format(collection['publishedfileid']))

        for c in collection['children']:
            filetype = c['filetype']
            if nested_collections and filetype == 2:
                # Recursion on nested collections, hopefully we don't run into an infinite loop
                workshop_items = workshop_items + get_collection_workshop_ids([c['publishedfileid']])
            elif filetype == 0:
                mod = c['publishedfileid']
                if mod not in workshop_items:
                    workshop_items.append(mod)
            else:
                click.echo("Unknown filetype encountered: '{}' on published file: '{}'".format(filetype,
                                                                                               c['publishedfileid']))

    return workshop_items


# https://steamapi.xpaw.me/#ISteamRemoteStorage/GetCollectionDetails
def get_collection_details(collection_ids):
    return STEAM_WEBAPI.ISteamRemoteStorage.GetCollectionDetails(collectioncount=len(collection_ids),
                                                                 publishedfileids=collection_ids)['response']


# https://steamapi.xpaw.me/#ISteamRemoteStorage/GetPublishedFileDetails
def get_published_file_details(published_file_ids):
    return STEAM_WEBAPI.ISteamRemoteStorage.GetPublishedFileDetails(itemcount=len(published_file_ids),
                                                                    publishedfileids=published_file_ids)['response']


def setup(config_path):
    # General configuration
    configuration = {
        'arma_appid': 107410,
        'server_appid': 233780,
        'steamcmd_dir': click.prompt('Enter install path for SteamCMD',
                                     default='SteamCMD', show_default=True,
                                     type=click.Path(file_okay=False, resolve_path=True)),
        'install_dir': click.prompt('Enter install path for Arma server',
                                    default='server', show_default=True,
                                    type=click.Path(file_okay=False, resolve_path=True)),
        'mod_dir': click.prompt('Enter steam install path for mods',
                                default='mods', show_default=True,
                                type=click.Path(file_okay=False, resolve_path=True)),
        'external_addon_dir': click.prompt('Enter directory to search for external addons',
                                           default='mods/external', show_default=True,
                                           type=click.Path(file_okay=False, resolve_path=True)),
        'cdlc': list(map(int, (click.prompt("List of CDLCs, separated by spaces", default='').split()))),
        'collections': list(map(int, (click.prompt("List of Collections, separated by spaces", default='').split()))),
        'handle_keys': click.confirm('Handle bikey files automatically', default=False, show_default=True),
        'api_key': click.prompt('Enter Steam API key (https://steamcommunity.com/dev/apikey)'),
    }

    # Create directories
    if not os.path.exists(configuration['steamcmd_dir']):
        os.makedirs(configuration['steamcmd_dir'])
    if not os.path.exists(configuration['install_dir']):
        os.makedirs(configuration['install_dir'])
    if not os.path.exists(configuration['mod_dir']):
        os.makedirs(configuration['mod_dir'])
    if not os.path.exists(configuration['external_addon_dir']):
        os.makedirs(configuration['external_addon_dir'])

    configuration['mod_dir_full'] = os.path.join(configuration['mod_dir'], 'steamapps',
                                                 'workshop', 'content', str(ARMA_APPID))

    # ArmA3Sync Configuration
    from a3update import arma3sync
    arma3sync._setup(configuration)

    # Swifty Configuration
    from a3update import swifty
    swifty._setup(configuration)

    # Launcher Preset Configuration
    from a3update import html_preset
    html_preset._setup(configuration)

    with open(config_path, 'w') as f:
        f.write(yaml.safe_dump(configuration))
        click.echo('Dumped configuration to: {}'.format(config_path))


if __name__ == '__main__':
    cli()
