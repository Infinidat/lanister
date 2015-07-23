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

def _encode_mac(mac):
    # turns 0A:1b:2c:3D:4e:5F or 0A1b2C3d4E5f into 0a1b.2c3d.4e5f (switch format)
    mac = mac.lower().replace(':','')
    return '%s.%s.%s' % (mac[0:4], mac[4:8], mac[8:12])

def _decode_mac(mac):
    # turns 0a1b.2c3d.4e5f (switch format) into 0a:1b:2c:3d:4e:5f
    mac = mac.lower().replace('.','')
    return '%s:%s:%s:%s:%s:%s' % (mac[0:2], mac[2:4], mac[4:6], mac[6:8], mac[8:10], mac[10:12])

@views.route("/")
def index():
    return Response('', mimetype='text/plain')

@views.route("/api/interfaces/", methods=['GET'])
def interface_list():
    if 'macs' in request.args:
        macs = [_encode_mac(mac) for mac in request.args['macs'].split(',') if mac]
        output, errout = _exec_command('show mac address-table | i "%s"' % ('|'.join(macs)))
        ports = {}
        for port in [i for i in output.strip().split('\n') if i]:
            port = port.split()
            ports[_decode_mac(port[2].strip())] = port[-1].strip()
        return jsonify(dict(ports=ports))
    if 'descriptions' in request.args:
        descriptions = [i for i in request.args['descriptions'].split(',') if i]
        output, errout = _exec_command('show interface description | i %s' % ('|'.join(descriptions)))
        ports = {}
        for port in [i for i in output.strip().split('\n') if i]:
            port = port.split()
            ports[port[-1].strip()] = port[0].strip()
        return jsonify(dict(ports=ports))
    output, errout = _exec_command('show interface brief')
    #TODO: parse this to json
    return Response(output, mimetype='text/plain')

@views.route("/api/interfaces/<interface_name>/", methods=['PUT','GET'])
def interface(interface_name):
    interface_name = interface_name.replace('_','/')
    if request.method == 'PUT':
        data = request.get_json(force=True)
        if 'bind' in data:
            # bind can be a channel or None
            command = ''
            if data['bind']:
                command = 'channel-group %s mode active' % (data['bind'])
            else:
                command = 'no channel-group'
            output, errout = _exec_command('config t ; interface %s ; %s ; exit' % (interface_name, command))
            if errout:
                abort(500, 'Error %s on switch when executing %s on %s' % (errout, command, interface_name))
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
    output, errout = _exec_command('show running-config interface %s' % (interface_name))
    config = [i.strip() for i in output.split(interface_name.replace('Eth',''))[-1].strip().split('\n')]
    return jsonify(dict(name=interface_name, config=config))

@views.route("/api/channels/<channel_name>/", methods=['POST','GET','DELETE'])
def channel(channel_name):
    if request.method == 'POST':
        output, errout = _exec_command('show interface brief | i Po%s' % (channel_name))
        if output:
            abort(400, 'Channel group Po%s already exists' % (channel_name))
        data = request.get_json(force=True, silent=True)
        command = 'config t ; interface port-channel %s' % (channel_name)
        if data and 'config' in data:
            command += ' ; %s' % (' ; '.join(data['config']))
        if data and 'description' in data:
            command += ' ; %s' % (data['description'])
        output, error = _exec_command(command)
        if 'Cmd exec error' in output:
            abort(500, 'Error %s in output while creating port-channel %s' % (output, channel_name))
    else:
        output, errout = _exec_command('show interface brief | i Po%s' % (channel_name))
        if not output:
            abort(404, 'No such channel group %s' % (channel_name))
        if request.method == 'DELETE':
            output, error = _exec_command('config t ; no interface port-channel %s ; exit' % (channel_name))
            return Response(output, mimetype='text/plain')
    output, errout = _exec_command('show running-config interface port-channel%s' % (channel_name))
    config = [i.strip() for i in output.split('port-channel%s' % (channel_name))[-1].strip().split('\n')]
    return jsonify(dict(name='port-channel%s' % (channel_name), config=config))
