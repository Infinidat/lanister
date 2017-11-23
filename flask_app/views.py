from flask import render_template, Blueprint, jsonify, request, abort, Response, current_app
from paramiko.client import SSHClient, AutoAddPolicy
import sys
import random

views = Blueprint("views", __name__, template_folder="templates")

def _exec_command(command, switch_name=''):
    if not switch_name:
        switch_name = [s for s in current_app.config['switches']][0]
    current_app.logger.info('running on %s: %s' % (switch_name, command))
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(current_app.config['switches'][switch_name]['address'],
            username=current_app.config['switches'][switch_name]['user'],
            key_filename=current_app.config['switches'][switch_name]['key'])
    sin, sout, serr = client.exec_command(command)
    output = sout.read().decode('ascii')
    errout = serr.read().decode('ascii')
    client.close()
    if errout or 'Cmd exec error' in output:
        abort(500, "Error executing '%s' on %s" % (command, switch_name))
    current_app.logger.info('output from %s: %s' % (switch_name, output))
    return output, errout

def _encode_mac(mac):
    # turns 0A:1b:2c:3D:4e:5F or 0A1b2C3d4E5f into 0a1b.2c3d.4e5f (switch format)
    if ':' in mac:
        mac = mac.lower().replace(':','')
        return '%s.%s.%s' % (mac[0:4], mac[4:8], mac[8:12])
    return mac

def _decode_mac(mac):
    # turns 0a1b.2c3d.4e5f (switch format) into 0a:1b:2c:3d:4e:5f
    mac = mac.lower().replace('.','')
    return '%s:%s:%s:%s:%s:%s' % (mac[0:2], mac[2:4], mac[4:6], mac[6:8], mac[8:10], mac[10:12])

@views.route("/")
def index():
    verb = current_app.config['verbs'][random.randint(0,len(current_app.config['verbs'])-1)]
    noun = current_app.config['nouns'][random.randint(0,len(current_app.config['nouns'])-1)]
    return Response('a LANister always %s their %s' % (verb, noun), mimetype='text/plain')

@views.route("/api/<switch_name>/interfaces/", methods=['GET'])
def interface_list(switch_name):
    if 'macs' in request.args:
        macs = [_encode_mac(mac) for mac in request.args['macs'].split(',') if mac]
        output, errout = _exec_command('show mac address-table | i "%s"' % ('|'.join(macs)), switch_name)
        ports = {}
        for port in [i for i in output.strip().split('\n') if i]:
            port = port.split()
            if 'Eth' in port[-1]:
                ports[_decode_mac(port[2].strip())] = port[-1].strip()
        return jsonify(dict(ports=ports))
    if 'descriptions' in request.args:
        descriptions = [i for i in request.args['descriptions'].split(',') if i]
        output, errout = _exec_command('show interface description | i %s' % ('|'.join(descriptions)), switch_name)
        ports = {}
        for port in [i for i in output.strip().split('\n') if i]:
            port = port.split()
            ports[port[-1].strip()] = port[0].strip()
        return jsonify(dict(ports=ports))
    output, errout = _exec_command('show interface brief', switch_name)
    #TODO: parse this to json
    return Response(output, mimetype='text/plain')

@views.route("/api/<switch_name>/interfaces/<interface_name>/", methods=['PUT','GET'])
def interface(switch_name, interface_name):
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
            output, errout = _exec_command('config t ; interface %s ; %s ; exit' % (interface_name, command),
                    switch_name)
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
                    (ifname, command), switch_name)
    output, errout = _exec_command('show running-config interface %s' % (interface_name), switch_name)
    config = [i.strip() for i in output.split(interface_name.replace('Eth',''))[-1].strip().split('\n')]
    return jsonify(dict(name=interface_name, config=config))

@views.route("/api/<switch_name>/channels/<channel_name>/", methods=['POST','GET','DELETE'])
def channel(switch_name, channel_name):
    if request.method == 'POST':
        output, errout = _exec_command('show interface brief | i Po%s' % (channel_name), switch_name)
        if output:
            abort(400, 'Channel group Po%s already exists' % (channel_name))
        data = request.get_json(force=True, silent=True)
        command = 'config t ; interface port-channel %s' % (channel_name)
        if data and 'config' in data:
            command += ' ; %s' % (' ; '.join(data['config']))
        if data and 'description' in data:
            command += ' ; %s' % (data['description'])
        output, errout = _exec_command(command, switch_name)
    else:
        output, errout = _exec_command('show interface brief | i Po%s' % (channel_name), switch_name)
        if not output:
            abort(404, 'No such channel group %s' % (channel_name))
        if request.method == 'DELETE':
            output, errout = _exec_command('config t ; no interface port-channel %s ; exit' % (channel_name),
                    switch_name)
            return Response(output, mimetype='text/plain')
    output, errout = _exec_command('show running-config interface port-channel%s' % (channel_name), switch_name)
    config = [i.strip() for i in output.split('port-channel%s' % (channel_name))[-1].strip().split('\n')]
    return jsonify(dict(name='port-channel%s' % (channel_name), config=config))

@views.route("/api/<switch_name>/macaddresses/<mac_address>/", methods=['GET'])
def mac_address(switch_name, mac_address):
    mac_addresses = [_encode_mac(mac_address)]
    output, errout = _exec_command('show mac address-table | i "%s"' % ('|'.join(mac_addresses)), switch_name)
    macs = {}
    for line in [i for i in output.strip().split('\n') if i]:
        line = line.split()
        if 'Eth' in line[-1]:
            interface_description = line[-1].strip()
            output_desc, errout = _exec_command('show interface description | i %s' % (interface_description), switch_name)
            for desc_line in [i for i in output_desc.strip().split('\n') if i]:
                desc_line = desc_line.split()
                macs[_decode_mac(line[2].strip())] = dict(interface=line[-1].strip(),
                                                          slot=desc_line[-1].strip())
    return jsonify(dict(macs=macs))
