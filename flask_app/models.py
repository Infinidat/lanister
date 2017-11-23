from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.security import UserMixin, RoleMixin
import datetime

db = SQLAlchemy()

### Add models here

roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id', ondelete='CASCADE')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id', ondelete='CASCADE')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

class ManagedMixin(object):
    last_seen = db.Column(db.DateTime(), default=datetime.datetime.now)
    managed = db.Column(db.Boolean(), default=False)

    @classmethod
    def from_switch_object(cls, switch_obj):
        raise NotImplementedError()  # pragma: no cover

    @classmethod
    def get_or_create(cls, **kwargs):
        inst = cls.query.filter_by(**kwargs).first()
        if not inst:
            inst = cls(**kwargs)
            db.session.add(inst)
        return inst

_MAC_ADDRESS = db.String(255)

class Vlan(db.Model, ManagedMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
#    switches = db.relationship("Switch", secondary=vlan_switch, backref="vlans")
#    connected_macs = db.relationship("Mac", secondary=vlan_mac, backref="vlans")
#    connected_ports = db.relationship("Port", secondary=vlan_ports, backref="vlans")

class Switch(db.Model, ManagedMixin):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False)
    interfaces = db.relationship('Interface', backref=db.backref('switch'))
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    private_key = db.Column(db.String(2048), nullable=False)

class Port(db.Model, ManagedMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    type = db.Column(db.String(32))
    mode = db.Column(db.String(32))
    status = db.Column(db.String(32))
    reason = db.Column(db.String(64))
    description = db.Column(db.String(256))
    switch_id = db.Column(db.Integer, db.ForeignKey('switch.id', ondelete="CASCADE"))

class EthernetPort(Port):
    speed = db.Column(db.String(32))
    connected_macs = db.relationship('Mac', backref=db.backref('ethernet_port'))

class PortChannel(Port):
    protocol = db.Column(db.String(32))
    connected_eths = db.relationship('EthernetPort', backref=db.backref('port_channel'))
#    connected_macs = db.relationship('Mac', secondary=mac_port_channel, backref="port_cannels")

class Mac(db.Model, ManagedMixin):
    id = db.Column(_MAC_ADDRESS, primary_key=True)
    type = db.Column(db.String(32))
