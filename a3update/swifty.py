import json
import os
import sys
import click
import subprocess
import shutil
from a3update.a3update import _create_mod_link, _filename, _log


def _setup(config):
    if click.confirm("Use Swifty"):
        if sys.platform == 'linux' or sys.platform == 'linux2':
            click.echo('Note that running Swifty on Linux requires mono-complete')
        path_to_cli = click.prompt('Enter path to swifty-cli.exe',
                                   default='swifty-cli.exe', show_default=True,
                                   type=click.Path(exists=True, resolve_path=True, dir_okay=False))
        path_to_json = click.prompt('Enter output path for swifty repo.json',
                                    default='repo.json', show_default=True,
                                    type=click.Path(resolve_path=True, dir_okay=False))

        config['swifty'] = {
            'active': True,
            'path_to_cli': path_to_cli,
            'path_to_json': path_to_json,
            'output_path': click.prompt('Enter output path for repo',
                                        type=click.Path(exists=True, resolve_path=True, file_okay=False)),
        }

        swifty_dir = os.path.join(config['mod_dir'], 'swifty')
        os.makedirs(swifty_dir)
        os.makedirs(os.path.join(swifty_dir, 'optional'))
        swifty_config = {
            'repoName': click.prompt('Enter repo name'),
            'basePath': swifty_dir,
            'iconImagePath': 'icon.png',
            'repoImagePath': 'repo.png',
            'clientParameters': '-skipIntro',
            'repoBasicAuthentication': {
                'username': click.prompt('FTP Username (Leave blank if no authentication)',
                                         default='', show_default=True),
                'password': click.prompt('FTP Password (Leave blank if no authentication)',
                                         default='', show_default=True, hide_input=True),
            },
            'requiredMods': [{'modName': '@*', 'enabled': True}],
            'optionalMods': [{'modName': 'optional/@*', 'enabled': False}],
        }

        servers = []
        for i in range(0, click.prompt('Number of servers to add', type=int, default=0, show_default=True)):
            servers.append({
                'name': click.prompt('Enter server name'),
                'address': click.prompt('Enter server address'),
                'port': click.prompt('Enter server port', default=2302, type=int, show_default=True),
                'password': click.prompt('Enter server password', default=''),
                'battleEye': click.confirm('Use BattleEye', default=False, show_default=True),
            })

        swifty_config['servers'] = servers

        with click.open_file(path_to_json, 'w') as f:
            f.write(json.dumps(swifty_config))
            _log('Dumped swifty configuration to: {}'.format(path_to_json))
    else:
        config['swifty'] = {
            'active': False,
            'path_to_cli': None,
            'path_to_json': None,
            'output_path': None,
        }


def update(mods, config_yaml):

    repo_config = json.load(click.open_file(config_yaml['swifty']['path_to_json']))

    # Wipe current repo, to be recreated below
    for filename in os.listdir(repo_config['basePath']):
        if filename.startswith('@'):
            shutil.rmtree(os.path.join(repo_config['basePath'], filename))

    # for filename in os.listdir(os.path.join(repo_config['basePath'], 'optional')):
    #    if filename.startswith('@'):
    #        shutil.rmtree(os.path.join(config_yaml['a3sync']['directory'], filename))

    for filename in os.listdir(config_yaml['swifty']['output_path']):
        f = os.path.join(config_yaml['swifty']['output_path'], filename)
        if os.path.isfile(f):
            os.remove(f)
        else:
            shutil.rmtree(f)

    # Create symlinks to all mods used
    for mod in mods:
        _create_mod_link(
            os.path.join(config_yaml['mod_dir_full'], mod['published_file_id']),
            os.path.join(repo_config['basePath'], mod['folder_name'])
        )
    # Handle external addons
    external_addon_dir = config_yaml['external_addon_dir']
    if os.path.isdir(external_addon_dir):
        for filename in os.listdir(external_addon_dir):
            out_path = os.path.join(repo_config['basePath'], _filename(filename))
            if not os.path.exists(out_path):
                _create_mod_link(os.path.join(external_addon_dir, filename), out_path)
            else:
                _log('ERR: Conflicting external addon "{}"'.format(filename), e=True)

    if sys.platform == 'linux' or sys.platform == 'linux2':
        subprocess.call(['mono', config_yaml['swifty']['path_to_cli'], 'create',
                         config_yaml['swifty']['path_to_json'], config_yaml['swifty']['output_path']])
    else:
        subprocess.call([config_yaml['swifty']['path_to_cli'], 'create',
                        config_yaml['swifty']['path_to_json'], config_yaml['swifty']['output_path']])
