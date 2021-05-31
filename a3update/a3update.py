import click
import os
import yaml
import shutil
from pysteamcmdwrapper import SteamCMD, SteamCMDException
from steam.webapi import WebAPI
from pathvalidate import sanitize_filename, sanitize_filepath

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

    with click.open_file(config, 'r') as file:
        global CONFIG_YAML
        CONFIG_YAML = yaml.safe_load(file)

    # Login to SteamCMD and WebAPI
    _log("Checking SteamCMD install")
    global STEAM_CMD
    STEAM_CMD = SteamCMD(CONFIG_YAML['steamcmd_dir'])
    try:
        STEAM_CMD.install()
    except SteamCMDException:
        click.echo("SteamCMD installed")
    STEAM_CMD.login(username, password)
    global STEAM_WEBAPI
    STEAM_WEBAPI = WebAPI(key=CONFIG_YAML['api_key'], https=False)

    # Load constants
    global WORKSHOP_DIR
    WORKSHOP_DIR = CONFIG_YAML['mod_dir_full']
    global INSTALL_DIR
    INSTALL_DIR = CONFIG_YAML['install_dir']
    global KEY_PATH
    KEY_PATH = os.path.join(INSTALL_DIR, 'keys')
    global EXTERNAL_ADDON_DIR
    EXTERNAL_ADDON_DIR = CONFIG_YAML['external_addon_dir']

    # Update apps (Arma 3 Dedicated Server, CDLCs)
    _log('Updating Arma 3 Server')
    if not no_update:
        beta = CONFIG_YAML['beta']
        if beta:
            STEAM_CMD.app_update(CONFIG_YAML['server_appid'], INSTALL_DIR, validate, beta)
        else:
            STEAM_CMD.app_update(CONFIG_YAML['server_appid'], INSTALL_DIR, validate)

    # Update mods
    _log('Updating mods')
    for filename in os.listdir(INSTALL_DIR):
        if filename.startswith('@'):
            shutil.rmtree(os.path.join(INSTALL_DIR, filename))

    if CONFIG_YAML['handle_keys']:
        # Delete key symlinks
        for filename in os.listdir(KEY_PATH):
            f = os.path.join(KEY_PATH, filename)
            if os.path.islink(f):
                os.unlink(f)

    mods = _workshop_ids_to_mod_array(_get_collection_workshop_ids(CONFIG_YAML['collections']))
    with click.progressbar(mods, label='Mod update progress') as bar:
        for mod in bar:
            _log('Updating {}'.format(mod['name']))

            # Create symbolic links to keep files lowercase without renaming
            if not no_update:
                STEAM_CMD.workshop_update(ARMA_APPID, mod['published_file_id'],
                                          CONFIG_YAML['mod_dir'], validate, n_tries=25)
            path = os.path.join(WORKSHOP_DIR, mod['published_file_id'])
            _create_mod_link(
                path,
                os.path.join(INSTALL_DIR, mod['folder_name'])
            )

            if CONFIG_YAML['handle_keys']:
                # Create key symlinks
                if not _create_key_links(path):
                    _log('WARN: No bikeys found for: {}'.format(mod['name']), e=True)

    # Handle external addons
    if os.path.isdir(EXTERNAL_ADDON_DIR):
        for filename in os.listdir(EXTERNAL_ADDON_DIR):
            out_path = os.path.join(INSTALL_DIR, _filename(filename))
            if not os.path.exists(out_path):
                _create_mod_link(os.path.join(EXTERNAL_ADDON_DIR, filename), out_path)
            else:
                _log('ERR: Conflicting external addon "{}"'.format(filename), e=True)

    if CONFIG_YAML['a3sync']['active']:
        from a3update import arma3sync
        _log('Building ArmA3Sync Repo')
        arma3sync.update(mods, CONFIG_YAML)
        _log('Finished building ArmA3Sync Repo')

    if CONFIG_YAML['html_preset']['active']:
        from a3update import html_preset
        _log('Generating Arma Launcher Preset')
        html_preset.generate(mods, CONFIG_YAML)
        _log('Finished generating Arma Launcher Preset')

    if CONFIG_YAML['swifty']['active']:
        from a3update import swifty
        _log('Building Swifty Repo')
        swifty.update(mods, CONFIG_YAML)
        _log('Finished building Swifty Repo')

    _log('Finished!')


def _create_key_links(path):
    keys = _find_bikeys(path)
    linked_keys = []
    if keys:
        for key in keys:
            key_link = _filename(os.path.basename(key))
            key_path = os.path.join(KEY_PATH, key_link)
            if not os.path.exists(key_path):
                os.symlink(
                    key,
                    key_path
                )
                linked_keys.append(key_link)
            else:
                linked_keys.append(key_link)
                _log('WARN: Duplicate key: {}'.format(key_link), e=True)

    return linked_keys


def _find_bikeys(path):
    keys = []

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.lower().endswith('.bikey'):
                keys.append(os.path.join(root, file))
    return keys


def _filename(f):
    return sanitize_filename(f.lower().replace(' ', '_'), platform='auto')


def _log(t, e=False):
    click.echo("", err=e)
    click.echo("{{0:=<{}}}".format(len(t)).format(""), err=e)
    click.echo(t, err=e)
    click.echo("{{0:=<{}}}".format(len(t)).format(""), err=e)


def _create_mod_link(input_path, output_path):
    if os.path.isdir(output_path):
        shutil.rmtree(output_path)

    os.mkdir(sanitize_filepath(output_path, platform='auto'))

    for filename in os.listdir(input_path):
        f = os.path.join(input_path, filename)
        if os.path.isdir(f):
            _create_mod_link(
                f,
                os.path.join(
                    output_path,
                    _filename(filename)
                )
            )
        else:
            os.symlink(
                f,
                os.path.join(
                    output_path,
                    _filename(filename)
                )
            )


def _workshop_ids_to_mod_array(workshop_ids):
    published_file_details = _get_published_file_details(workshop_ids)

    mod_arr = []
    for i in range(0, published_file_details['resultcount']):
        file_details = published_file_details['publishedfiledetails'][i]

        mod_arr.append({
            'name': file_details['title'],
            'folder_name': '@{}'.format(_filename(file_details['title'])),
            'published_file_id': file_details['publishedfileid'],
        })

    return mod_arr


def _get_collection_workshop_ids(collection_ids, nested_collections=True):
    workshop_items = []
    collection_details = _get_collection_details(collection_ids)

    for i in range(0, collection_details['resultcount']):
        collection = collection_details['collectiondetails'][i]
        click.echo('Processing collection "{}"'.format(
            _get_published_file_details([collection['publishedfileid']])['publishedfiledetails'][0]['title']
        ))

        for c in collection['children']:
            filetype = c['filetype']
            if nested_collections and filetype == 2:
                # Recursion on nested collections, hopefully we don't run into an infinite loop
                workshop_items = workshop_items + _get_collection_workshop_ids([c['publishedfileid']])
            elif filetype == 0:
                mod = c['publishedfileid']
                if mod not in workshop_items:
                    workshop_items.append(mod)
            else:
                _log(
                    "Unknown filetype encountered: '{}' on published file: '{}'".format(filetype, c['publishedfileid']),
                    e=True
                )

    return workshop_items


# https://steamapi.xpaw.me/#ISteamRemoteStorage/GetCollectionDetails
def _get_collection_details(collection_ids):
    response = STEAM_WEBAPI.ISteamRemoteStorage.GetCollectionDetails(collectioncount=len(collection_ids),
                                                                     publishedfileids=collection_ids)
    if 'response' in response:
        response = response['response']
        if response['resultcount'] != len(collection_ids):
            _log("""
                Querying Steam API for collections {} only returned {} collections. 
                Check collection visibility and ID
                """.format(collection_ids, response['resultcount']), e=True)
        return response
    else:
        _log('Querying Steam API for collections {} returned no response'.format(collection_ids), e=True)
        return {}


# https://steamapi.xpaw.me/#ISteamRemoteStorage/GetPublishedFileDetails
def _get_published_file_details(published_file_ids):
    response = STEAM_WEBAPI.ISteamRemoteStorage.GetPublishedFileDetails(itemcount=len(published_file_ids),
                                                                        publishedfileids=published_file_ids)
    if 'response' in response:
        response = response['response']
        if response['resultcount'] != len(published_file_ids):
            _log("""
                Querying Steam API for workshop items {} only returned {} items. 
                Check item visibility and ID"""
                 .format(published_file_ids, response['resultcount']), e=True)
        return response
    else:
        _log('Querying Steam API for workshop items {} returned no response'.format(published_file_ids), e=True)
        return {}


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
        'beta': click.prompt('Beta branch', default=''),
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

    with click.open_file(config_path, 'w') as f:
        f.write(yaml.safe_dump(configuration))
        _log('Dumped configuration to: {}'.format(config_path))


if __name__ == '__main__':
    cli()
