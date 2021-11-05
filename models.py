#!venv/bin/python

from flask_security import UserMixin, RoleMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Define models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

doits_didits = db.Table(
    'doits_didits',
    db.Column('doit_id', db.Integer(), db.ForeignKey('doit.id')),
    db.Column('didit_id', db.Integer(), db.ForeignKey('didit.id'))
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __str__(self):
        return self.name


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))


class DoIt(db.Model):
    __tablename__ = 'doit'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=False)

    def __str__(self):
        return self.description


class DidIt(db.Model):
    __tablename__ = 'didit'
    id = db.Column(db.Integer, primary_key=True)
    done_at = db.Column(db.DateTime())
    do_it = db.relationship('DoIt', secondary=doits_didits,
                            backref=db.backref('doit'))


