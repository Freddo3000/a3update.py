import os
import click
import subprocess
import shutil
import tempfile
from a3update.a3update import _create_mod_link, _filename, _log


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
                                        type=click.Path(exists=True, resolve_path=True, file_okay=False))
        config['a3sync'] = {
            'active': True,
            'path_to_jar': path_to_jar,
            'repo_name': repo_name,
            'directory': shared_directory,
        }
    else:
        config['a3sync'] = {
            'active': False,
            'path_to_jar': None,
            'repo_name': None,
            'directory': None,
        }


def update(mods, config_yaml):
    output_dir = config_yaml['a3sync']['directory']

    # Store .zsync files in a temporary directory
    zsync_storage = tempfile.mkdtemp()
    cache_count = 0
    for root, dirs, files in os.walk(output_dir):
        temp_dir = os.path.join(zsync_storage, os.path.relpath(root, output_dir))

        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)

        for f in files:
            if f.endswith('.zsync'):
                cache_count += 1
                shutil.copy(os.path.join(root, f), os.path.join(temp_dir, f))

    print('Cached .zsync files:', cache_count)

    # Wipe current repo, to be recreated below
    for filename in os.listdir(output_dir):
        if filename.startswith('@'):
            shutil.rmtree(os.path.join(output_dir, filename))

    # Create symlinks to all mods used
    for mod in mods:
        _create_mod_link(
            os.path.join(config_yaml['mod_dir_full'], mod['published_file_id']),
            os.path.join(output_dir, mod['folder_name'])
        )
    # Handle external mods
    external_addon_dir = config_yaml['external_addon_dir']
    if os.path.isdir(external_addon_dir):
        for filename in os.listdir(external_addon_dir):
            out_path = os.path.join(output_dir, _filename(filename))
            if not os.path.exists(out_path):
                _create_mod_link(os.path.join(external_addon_dir, filename), out_path)
            else:
                _log('ERR: Conflicting external addon "{}"'.format(filename), e=True)

    # Retrieve stored .zsync files
    uncache_count = 0
    for root, dirs, files in os.walk(output_dir):
        temp_dir = os.path.join(zsync_storage, os.path.relpath(root, output_dir))

        for f in files:
            zsync = f.join('.zsync')
            if os.path.exists(zsync):
                uncache_count += 1
                shutil.copy(os.path.join(temp_dir, zsync), os.path.join(root, zsync))
    print('Reused .zsync files:', uncache_count)

    subprocess.call(['java', '-jar',
                     config_yaml['a3sync']['path_to_jar'],
                     '-build', config_yaml['a3sync']['repo_name']])
