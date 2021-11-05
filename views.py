#!venv/bin/python
import datetime

from flask import url_for, redirect, request, abort, flash
from flask_admin import BaseView, expose
from flask_admin.babel import gettext
from flask_admin.contrib import sqla
from flask_admin.helpers import get_form_data
from flask_security import current_user
from markupsafe import Markup
from wtforms import PasswordField


# Create customized model view class
from models import DidIt


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
