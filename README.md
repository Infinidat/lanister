Lanister
=============

Lanister is a Nexus switch manager, until something better comes along. It's
based on [weber-minimal](https://github.com/vmalloc/weber-minimal) and is
distributed under the BSD 3-clause license. Weber is as well, and the original
license has been maintained as WEBER-LICENSE

Running
============
1. Check out the repository

2. Go through the configuration in `flask_app/app.yml` - most configuration
   options there are self-explanatory, and you might be interested in tweaking
   them to your needs.

3. Make sure you have `virtualenv` installed

4. Run the test server to experiment:

```
$ python manage.py testserver
```

Usage
============

Interface lookup in MAC address table:
```
$ curl http://127.0.0.1:8000/api/SW01/interfaces/\?macs=ecf4bbd60324,bc305bf6b830
{
  "ports": {
    "bc:30:5b:f6:b8:30": "Eth13/47",
    "ec:f4:bb:d6:03:24": "Eth101/1/5"
  }
}
```

Interface lookup by description:
```
$ curl http://127.0.0.1:8000/api/SW02/interfaces/\?descriptions=SLOT48.NODE3.DATA1,SLOT48.NODE2.DATA1
{
  "ports": {
    "SLOT48.NODE2.DATA1": "Eth17/41",
    "SLOT48.NODE3.DATA1": "Eth17/40"
  }
}
```

Interface running configuration:
```
$ curl http://127.0.0.1:8000/api/SW01/interfaces/Eth17_41/
{
  "config": [
    "description SLOT48.NODE2.DATA1",
    "switchport",
    "switchport mode trunk",
    "switchport trunk native vlan 4",
    "switchport trunk allowed vlan 4,10-11",
    "spanning-tree port type edge trunk",
    "mtu 9216",
    "no shutdown"
  ],
  "name": "Eth17/41"
}
```

Interface shutdown:
```
$ curl http://127.0.0.1:8000/api/SW01/interfaces/Eth17_41/ -d '{"state":"down"}' -X PUT
{
  "config": [
    "description SLOT48.NODE2.DATA1",
    "switchport",
    "switchport mode trunk",
    "switchport trunk native vlan 4",
    "switchport trunk allowed vlan 4,10-11",
    "spanning-tree port type edge trunk",
    "mtu 9216"
  ],
  "name": "Eth17/41"
}
```

Interface no shutdown:
```
$ curl http://127.0.0.1:8000/api/SW01/interfaces/Eth17_41/ -d '{"state":"up"}' -X PUT
{
  "config": [
    "description SLOT48.NODE2.DATA1",
    "switchport",
    "switchport mode trunk",
    "switchport trunk native vlan 4",
    "switchport trunk allowed vlan 4,10-11",
    "spanning-tree port type edge trunk",
    "mtu 9216",
    "no shutdown"
  ],
  "name": "Eth17/41"
}
```

Port channel creation and configuration
```
$ curl http://127.0.0.1:8000/api/SW01/channels/48/3/ -d '{"config":["switchport","switchport mode trunk","switchport trunk native vlan 4","switchport trunk allowed vlan 4,10-11","mtu 9216","no shutdown"]}' -X POST
{
  "config": [
    "description SLOT48.NODE3.LACP",
    "switchport",
    "switchport mode trunk",
    "switchport trunk native vlan 4",
    "switchport trunk allowed vlan 4,10-11",
    "mtu 9216"
  ],
  "name": "port-channel2483"
}
```

Interface channel group binding:
```
$ curl http://127.0.0.1:8000/api/SW01/interfaces/Eth17_41/ -d '{"bind":"2483"}' -X PUT
{
  "config": [
    "description SLOT48.NODE2.DATA1",
    "switchport",
    "switchport mode trunk",
    "switchport trunk native vlan 4",
    "switchport trunk allowed vlan 4,10-11",
    "spanning-tree port type edge trunk",
    "mtu 9216",
    "channel-group 2483 mode active",
    "no shutdown"
  ],
  "name": "Eth17/41"
}
```

Interface channel group unbinding:
```
$ curl http://127.0.0.1:8000/api/SW01/interfaces/Eth17_41/ -d '{"bind":""}' -X PUT
{
  "config": [
    "description SLOT48.NODE2.DATA1",
    "switchport",
    "switchport mode trunk",
    "switchport trunk native vlan 4",
    "switchport trunk allowed vlan 4,10-11",
    "spanning-tree port type edge trunk",
    "mtu 9216",
    "no shutdown"
  ],
  "name": "Eth17/41"
}
```

Port channel deletion:
```
$ curl http://127.0.0.1:8000/api/SW01/channels/48/3/ -X DELETE
```
