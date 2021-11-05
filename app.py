#!venv/bin/python
import os

import flask_admin
from flask import Flask, url_for, render_template
from flask_admin import helpers as admin_helpers
from flask_security import Security, SQLAlchemyUserDatastore

# Create Flask application
from models import db, User, Role, DoIt, DidIt
from views import MyModelView, UserView, DoItView, DidItView, CustomView

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


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


if __name__ == '__main__':

    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()

    # Start app
    app.run(debug=True)
