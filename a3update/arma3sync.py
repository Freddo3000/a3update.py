import os
import click
import subprocess
import shutil


def _setup(config):
    if click.confirm("Use ArmA3Sync"):
        click.echo('Note that this requires Java to be installed')
        path_to_jar = click.prompt('Enter path to ArmA3Sync.jar',
                                   type=click.Path(exists=True, resolve_path=True, dir_okay=False))
        if not click.confirm('Have you created an ArmA3Sync repo? Enter no to open ArmA3Sync cli'):
            click.echo('When prompted select "NEW" from the list of options to create a new repo')
            subprocess.call(['java', '-jar', path_to_jar, '-console'])

        repo_name = click.prompt('Enter ArmA3Sync Repo Name')
        shared_directory = click.prompt('Enter path to shared directory',
                                        type=click.Path(resolve_path=True, file_okay=False))
        config['a3sync'] = {
            'active': True,
            'path_to_jar': path_to_jar,
            'repo_name': repo_name,
            'directory': shared_directory,
        }
        click.echo('Opening ArmA3Sync repo creation prompt...')
    else:
        config['a3sync'] = {
            'active': False,
            'path_to_jar': None,
            'repo_name': None,
            'directory': None,
        }


def update(mods, config_yaml):
    from a3update.a3update import create_mod_link

    # Wipe current repo, to be recreated below
    for filename in os.listdir(config_yaml['a3sync']['directory']):
        f = os.path.join(config_yaml['a3sync']['directory'], filename)
        if f.startswith('@'):
            shutil.rmtree(f)

    # Create symlinks to all mods used
    for mod in mods:
        create_mod_link(
            os.path.join(config_yaml['mod_dir_full'], mod['published_file_id']),
            os.path.join(config_yaml['a3sync']['directory'], mod['folder_name'])
        )

    subprocess.call(['java', '-jar',
                     config_yaml['a3sync']['path_to_jar'],
                     '-build', config_yaml['a3sync']['repo_name']])
