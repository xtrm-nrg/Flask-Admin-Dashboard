#!venv/bin/python
import datetime
import os
from flask import Flask, url_for, redirect, render_template, request, abort, flash
from flask_admin.babel import gettext
from flask_admin.helpers import get_form_data
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required, current_user
from flask_security.utils import encrypt_password
import flask_admin
from flask_admin.contrib import sqla
from flask_admin import helpers as admin_helpers
from flask_admin import BaseView, expose
from markupsafe import Markup
from wtforms import PasswordField
from flask_admin.form import rules
from sqlalchemy.orm import relationship

# Create Flask application
app = Flask(__name__)
app.config.from_pyfile('config.py')
db = SQLAlchemy(app)

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


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        if not current_user.is_active or not current_user.is_authenticated:
            return False

        if current_user.has_role('superuser'):
            return True

        return False

    def _handle_view(self, name, **kwargs):
        """
        Override builtin _handle_view in order to redirect users when a view is not accessible.
        """
        if not self.is_accessible():
            if current_user.is_authenticated:
                # permission denied
                abort(403)
            else:
                # login
                return redirect(url_for('security.login', next=request.url))

    # can_edit = True
    edit_modal = True
    create_modal = True
    can_export = True
    can_view_details = True
    details_modal = True


class UserView(MyModelView):
    column_editable_list = ['email', 'first_name', 'last_name']
    column_searchable_list = column_editable_list
    column_exclude_list = ['password']
    # form_excluded_columns = column_exclude_list
    column_details_exclude_list = column_exclude_list
    column_filters = column_editable_list
    form_overrides = {
        'password': PasswordField
    }


class DoItView(MyModelView):
    column_list = ['name', 'description', 'do it now!']
    column_editable_list = ['name', 'description']
    column_searchable_list = column_editable_list
    column_exclude_list = ['id']
    column_details_exclude_list = column_exclude_list
    column_filters = column_editable_list

    def _format_do_it_now(view, context, model, name):

        # render a form with a submit button for student, include a hidden field for the student id
        # note how checkout_view method is exposed as a route below
        checkout_url = url_for('.did_it_view')

        _html = '''
            <form action="{checkout_url}" method="POST">
                <input id="do_it_id" name="do_it_id"  type="hidden" value="{do_it_id}">
                <button type='submit'>Do it!</button>
            </form
        '''.format(checkout_url=checkout_url, do_it_id=model.id)

        return Markup(_html)

    column_formatters = {
        'do it now!': _format_do_it_now
    }

    @expose('checkout', methods=['POST'])
    def did_it_view(self):

        return_url = self.get_url('.index_view')

        form = get_form_data()

        if not form:
            flash(gettext('Could not get form from request.'), 'error')
            return redirect(return_url)

        # Form is an ImmutableMultiDict
        do_it_id = form['do_it_id']

        # Get the model from the database
        model = self.get_one(do_it_id)

        if model is None:
            flash(gettext('Do it not not found.'), 'error')
            return redirect(return_url)

        # process the model
        flash(gettext(f"model is {type(model)}"))
        did_it = DidIt(do_it=[model], done_at=datetime.datetime.now())
        self.session.add(did_it)

        try:
            self.session.commit()
            flash(gettext(f"Recorded a didit for DoIt, ID: {do_it_id}, at {did_it.done_at}"))
        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise

            flash(gettext(f"Failed to Recorded a didit for DoIt, ID: {do_it_id}",
                          error=str(ex)), 'error')

        return redirect(return_url)


class DidItView(MyModelView):
    column_hide_backrefs = False
    column_list = ['do_it', 'done_at']
    column_details_list = ['description']
    column_editable_list = ['id', 'done_at']
    column_searchable_list = column_editable_list
    column_filters = column_editable_list


class CustomView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/custom_index.html')


# Flask views
@app.route('/')
def index():
    return render_template('index.html')


# Create admin
admin = flask_admin.Admin(
    app,
    'My Dashboard',
    base_template='my_master.html',
    template_mode='bootstrap4',
)

# Add model views
admin.add_view(MyModelView(Role, db.session, menu_icon_type='fa', menu_icon_value='fa-server', name="Roles"))
admin.add_view(UserView(User, db.session, menu_icon_type='fa', menu_icon_value='fa-users', name="Users"))
admin.add_view(DoItView(DoIt, db.session, menu_icon_type='fa', menu_icon_value='fa-clipboard-check', name="DoIts"))
admin.add_view(DidItView(DidIt, db.session, menu_icon_type='fa', menu_icon_value='fa-clipboard-check', name="DidIts"))
admin.add_view(
    CustomView(name="Custom view", endpoint='custom', menu_icon_type='fa', menu_icon_value='fa-connectdevelop', ))


# define a context processor for merging flask-admin's template context into the
# flask-security views.
@security.context_processor
def security_context_processor():
    return dict(
        admin_base_template=admin.base_template,
        admin_view=admin.index_view,
        h=admin_helpers,
        get_url=url_for
    )


def build_sample_db():
    """
    Populate a small db with some example entries.
    """

    import string
    import random

    db.drop_all()
    db.create_all()

    with app.app_context():
        user_role = Role(name='user')
        super_user_role = Role(name='superuser')
        db.session.add(user_role)
        db.session.add(super_user_role)
        db.session.commit()

        test_user = user_datastore.create_user(
            first_name='Admin',
            email='admin',
            password=encrypt_password('admin'),
            roles=[user_role, super_user_role]
        )

        first_names = [
            'Harry', 'Amelia', 'Oliver', 'Jack', 'Isabella', 'Charlie', 'Sophie', 'Mia',
            'Jacob', 'Thomas', 'Emily', 'Lily', 'Ava', 'Isla', 'Alfie', 'Olivia', 'Jessica',
            'Riley', 'William', 'James', 'Geoffrey', 'Lisa', 'Benjamin', 'Stacey', 'Lucy'
        ]
        last_names = [
            'Brown', 'Smith', 'Patel', 'Jones', 'Williams', 'Johnson', 'Taylor', 'Thomas',
            'Roberts', 'Khan', 'Lewis', 'Jackson', 'Clarke', 'James', 'Phillips', 'Wilson',
            'Ali', 'Mason', 'Mitchell', 'Rose', 'Davis', 'Davies', 'Rodriguez', 'Cox', 'Alexander'
        ]

        for i in range(len(first_names)):
            tmp_email = first_names[i].lower() + "." + last_names[i].lower() + "@example.com"
            tmp_pass = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(10))
            user_datastore.create_user(
                first_name=first_names[i],
                last_name=last_names[i],
                email=tmp_email,
                password=encrypt_password(tmp_pass),
                roles=[user_role, ]
            )

        fish = DoIt(name='Feed Fish', description="Feed the fish")
        maintenance = DoIt(name='Tank Maintenance', description="Change water, clean filters, vacuum sand")
        dishes = DoIt(name='Unload dishwasher', description="Unload dishwasher")
        laundry = DoIt(name='Do laundry', description="Do laundry")

        db.session.add(fish)
        db.session.add(maintenance)
        db.session.add(dishes)
        db.session.add(laundry)

        db.session.commit()
    return


if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()

    # Start app
    app.run(debug=True)
