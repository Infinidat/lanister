from flask import render_template, Blueprint, jsonify, request, abort, Response, current_app
import sys
from paramiko.client import SSHClient, AutoAddPolicy

views = Blueprint("views", __name__, template_folder="templates")

def _exec_command(command):
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(current_app.config['switch_name'], username=current_app.config['switch_user'],
            key_filename=current_app.config['switch_key'])
    sin, sout, serr = client.exec_command(command)
    output = sout.read().decode('ascii')
    errout = serr.read().decode('ascii')
    client.close()
    return output, errout

@views.route("/")
def index():
    output, errout = _exec_command('show interface brief')
    return Response(output, mimetype='text/plain')

@views.route("/api/interfaces/<interface_name>/", methods=['PUT','GET'])
def interface(interface_name):
    interface_name = interface_name.replace('_','/')
    if request.method == 'PUT':
        data = request.get_json(force=True)
        if 'state' in data:
            command = ''
            if data['state'] == 'down':
                command = 'shutdown'
            elif data['state'] == 'up':
                command = 'no shutdown'
            else:
                abort(400, '"state" must be "up" or "down" in interface configuration')
            ifname = interface_name.replace('Eth','')
            output, errout = _exec_command('config ; interface ethernet %s ; %s ; exit ; exit' %
                    (ifname, command))
            if errout:
                abort(500, 'Error %s on switch when executing %s on %s' % (errout, command, interface_name))
    output, errout = _exec_command('show interface %s' % (interface_name))
    return Response(output, mimetype='text/plain')
