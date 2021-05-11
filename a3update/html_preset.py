import os.path
import click


def _setup(config):
    if click.confirm("Generate Arma 3 Preset"):
        preset_name = click.prompt('Enter Preset Name')
        path_to_html = click.prompt('Enter output path for preset .html',
                                    default=os.path.join(os.getcwd(), preset_name.lower().replace(' ', '_') + ".html"),
                                    show_default=True, type=click.Path(exists=False, resolve_path=True, dir_okay=False))
        config['html_preset'] = {
            'active': True,
            'path_to_html': path_to_html,
            'name': preset_name,
        }
    else:
        config['html_preset'] = {
            'active': False,
            'path_to_html': None,
            'name': None,
        }


def generate(mods, config):
    f = open(config['html_preset']['path_to_html'], "w")
    f.write(('<?xml version="1.0" encoding="utf-8"?>\n'
             '<html>\n\n'
             '<!--Created using a3update.py: https://gist.github.com/Freddo3000/a5cd0494f649db75e43611122c9c3f15-->\n'
             '<head>\n'
             '<meta name="arma:Type" content="{}" />\n'
             '<meta name="arma:PresetName" content="{}" />\n'
             '<meta name="generator" content="a3update.py">\n'
             ' <title>Arma 3</title>\n'
             '<link href="https://fonts.googleapis.com/css?family=Roboto" rel="stylesheet" type="text/css" />\n'
             '<style>\n'
             'body {{\n'
             'margin: 0;\n'
             'padding: 0;\n'
             'color: #fff;\n'
             'background: #000;\n'
             '}}\n'
             'body, th, td {{\n'
             'font: 95%/1.3 Roboto, Segoe UI, Tahoma, Arial, Helvetica, sans-serif;\n'
             '}}\n'
             'td {{\n'
             'padding: 3px 30px 3px 0;\n'
             '}}\n'
             'h1 {{\n'
             'padding: 20px 20px 0 20px;\n'
             'color: white;\n'
             'font-weight: 200;\n'
             'font-family: segoe ui;\n'
             'font-size: 3em;\n'
             'margin: 0;\n'
             '}}\n'
             'h2 {{'
             'color: white;'
             'padding: 20px 20px 0 20px;'
             'margin: 0;'
             '}}'
             'em {{\n'
             'font-variant: italic;\n'
             'color:silver;\n'
             '}}\n'
             '.before-list {{\n'
             'padding: 5px 20px 10px 20px;\n'
             '}}\n'
             '.mod-list {{\n'
             'background: #282828;\n'
             'padding: 20px;\n'
             '}}\n'
             '.optional-list {{\n'
             'background: #222222;\n'
             'padding: 20px;\n'
             '}}\n'
             '.dlc-list {{\n'
             'background: #222222;\n'
             'padding: 20px;\n'
             '}}\n'
             '.footer {{\n'
             'padding: 20px;\n'
             'color:gray;\n'
             '}}\n'
             '.whups {{\n'
             'color:gray;\n'
             '}}\n'
             'a {{\n'
             'color: #D18F21;\n'
             'text-decoration: underline;\n'
             '}}\n'
             'a:hover {{\n'
             'color:#F1AF41;\n'
             'text-decoration: none;\n'
             '}}\n'
             '.from-steam {{\n'
             'color: #449EBD;\n'
             '}}\n'
             '.from-local {{\n'
             'color: gray;\n'
             '}}\n'
             ).format("Modpack", config['html_preset']['name']))

    f.write(('</style>\n'
             '</head>\n'
             '<body>\n'
             '<h1>Arma 3  - {} <strong>{}</strong></h1>\n'
             '<p class="before-list">\n'
             '<em>Drag this file or link to it to Arma 3 Launcher or open it Mods / Preset / Import.</em>\n'
             '</p>\n'
             '<h2 class="list-heading">Required Mods</h2>'
             '<div class="mod-list">\n'
             '<table>\n'
             ).format("Modpack", config['html_preset']['name']))

    for mod in mods:
        url = 'https://steamcommunity.com/sharedfiles/filedetails/?id={}'.format(mod['published_file_id'])
        f.write(('<tr data-type="ModContainer">\n'
                 '<td data-type="DisplayName">{}</td>\n'
                 '<td>\n'
                 '<span class="from-steam">Steam</span>\n'
                 '</td>\n'
                 '<td>\n'
                 '<a href="{}" data-type="Link">{}</a>\n'
                 '</td>\n'
                 '</tr>\n'
                 ).format(mod['name'], url, url))
    f.write('</table>\n'
            '</div>\n'
            '<div class="footer">\n'
            '<span>Created using a3update.py by Freddo3000.</span>\n'
            '</div>\n'
            '</body>\n'
            '</html>\n'
            )
