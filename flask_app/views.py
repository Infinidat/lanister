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

@views.route("/api/channels/<int:slot_num>/<int:node_num>/", methods=['POST','GET','DELETE'])
def channel(slot_num, node_num):
    #find DATA1 and DATA2, abort if they don't exist
    d1out, d1err = _exec_command('show interface description | i SLOT%d.NODE%d.DATA1' % (slot_num, node_num))
    if not d1out:
        abort(404, 'No DATA1 port found for SLOT%d NODE%d' % (slot_num, node_num))
    #d2out, d2err = _exec_command('show interface description | i SLOT%d.NODE%d.DATA2' % (slot_num, node_num))
    #if not d2out:
    #    abort(404, 'No DATA2 port found for SLOT%d NODE%d' % (slot_num, node_num))
    d1 = d1out.split()[0]
    #d2 = d2out.split()[0]
    print(d1)
    #print(d2)
    channel_name = '2%d%d' % (slot_num, node_num)
    output, errout = _exec_command('show interface brief | i Po%s' % (channel_name))
    if request.method == 'POST':
        if output:
            abort(400, 'Channel group Po%s already exists' % (channel_name))
        # create the channel group and bind DATA1 and DATA2 to it
        output, error = _exec_command('show running-config interface %s' % (d1))
        print(output)
        config = [i.strip() for i in output.split('SLOT%d.NODE%d.DATA1'
            % (slot_num, node_num))[-1].strip().split('\n')]
        #output, error = _exec_command('show running-config interface %s' % (d2))
        if any([i for i in config if 'channel-group' in i]): # or 'channel-group' in output
            abort(400, 'SLOT%d NODE%d DATA1 already in a channel group' % (slot_num, node_num))
        output, error = _exec_command('config t ; interface port-channel %s ; %s ; description SLOT%d.NODE%d.LACP' % (channel_name, ' ; '.join(config), slot_num, node_num))
        print(output)
        if 'Cmd exec error' in output:
            abort(500, 'Error %s in output while creating port-channel %s' % (output, channel_name))
        output, error = _exec_command('config t ; interface %s ; channel-group %s mode active ; exit' %
                (d1, channel_name))
        print(output)
#        output, error = _exec_command('config t ; interface %s ; channel-group %s mode active ; exit' %
#                (d2, channel_name))
    else:
        if not output:
            abort(404, 'No such channel group Po2%d%d' % (slot_num, node_num))
        if request.method == 'DELETE':
            output, error = _exec_command('config t ; no interface port-channel %s ; exit' % (channel_name))
            return Response(output, mimetype='text/plain')
    output, errout = _exec_command('show running-config interface port-channel2%d%d' % (slot_num, node_num))
    return Response(output, mimetype='text/plain')
