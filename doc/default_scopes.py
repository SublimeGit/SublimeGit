# coding: utf-8
import os
import plistlib
import webbrowser
import re


DIR = '/Users/mp/Library/Application Support/Sublime Text 2/Packages/Color Scheme - Default'
SCOPE_SIZE = 3
SCOPE_MATCH = lambda x: True


def scopefilter(scope):
    if not scope:
        return False
    if scope.startswith('.') or scope.startswith('-'):
        return False
    if len(scope.split('.')) > SCOPE_SIZE:
        return False
    if not SCOPE_MATCH(scope):
        return False
    return True


def generate_css(base, scope):
    base = dict(base)
    base.update(scope)
    css = ""
    if base.get('foreground'):
        css += "color: %s;" % base.get('foreground')
    if base.get('background'):
        css += "background: %s;" % base.get('background')
    if base.get('fontStyle'):
        s = base.get('fontStyle').lower()
        if 'bold' in s:
            css += "font-weight: bold;"
        if 'italic' in s:
            css += "font-style: italic;"
        if 'underline' in s:
            css += "text-decoration: underline;"
    return css


def main():
    files = [os.path.join(DIR, f) for f in os.listdir(DIR) if f.endswith('.tmTheme')]

    settings_keys = set()
    base_scopes = {}
    scopes = {}
    for f in files:
        plist = plistlib.readPlist(f)

        name = plist.get('name', os.path.basename(f))

        for s in plist.get('settings', []):
            namename = s.get('name', '').strip()
            scopename = s.get('scope', '').strip()
            if not namename and not scopename:
                settings = s.get('settings', {})
                settings_keys.update(settings.keys())
                base_scopes[name] = settings
            elif scopename:
                scopename = s.get('scope')
                settings = s.get('settings', {})
                settings_keys.update(settings.keys())
                for scope in re.split(r'[^a-zA-Z\.\-]', scopename):
                    if scopefilter(scope):
                        scopes.setdefault(scope.strip(), {})[name] = settings

    themes = list(sorted(base_scopes.keys()))
    scopenames = list(sorted(scopes.keys()))

    # write headers
    th = "<th>scope name</th>"
    for t in themes:
        th += '<th class="theme">%s</th>' % t

    # write rows
    tr = ""
    for s in scopenames:
        tr += '<tr>'
        tr += "<th>%s</th>" % s
        for t in themes:
            scope = scopes.get(s, {}).get(t, {})
            if scope:
                tr += '<td style="%s">test</td>' % generate_css(base_scopes.get(t), scope)
            else:
                tr += '<td style="%s"></td>' % generate_css(base_scopes.get(t), scope)
        tr += '</tr>'

    # write html file
    html = """<html>
    <head>
        <title>Theme comparisons</title>
        <style>
            body, table {
                font-family: sans-serif;
                font-size: 12px;
                white-space: nowrap;
            }
            table {
                border-spacing:0;
            }
            tbody th {
                text-align: left;
                margin: 0 5px;
            }
            tbody td {
                margin: 0px 5px;
                text-align:center;
                width: 200px;
            }
            tbody tr:hover td {
                border-color: #fff;
                border-style: solid;
                border-top-width: 2px;
                border-bottom-width: 2px;
                padding: 20px;
            }
            tbody tr:hover th {
                border-color: #f00;
                border-style: solid;
                border-top-width: 2px;
                border-bottom-width: 2px;
            }
        </style>
    </head>
    <body>
    <table>
        <thead>
            <tr>%(thead)s</tr>
        </thead>
        <tbody>
            %(tbody)s
        </tbody>
    </table>
    </body>""" % dict(thead=th, tbody=tr)

    with open('themes.html', 'w+') as f:
        f.write(html)

    webbrowser.open('file://localhost' + os.path.realpath('themes.html'))


if __name__ == "__main__":
    main()
